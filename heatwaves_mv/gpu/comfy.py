"""ComfyUI HTTP client used by the generation jobs (runs on the GPU machine)."""
import json
import mimetypes
import os
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


class Comfy:
    def __init__(self, url='http://127.0.0.1:8188', root=None):
        self.url = url.rstrip('/')
        self.root = root            # ComfyUI install dir (to copy outputs without HTTP)
        self.client_id = uuid.uuid4().hex

    # -- low level --------------------------------------------------------------------
    def _req(self, path, data=None, method=None, headers=None, timeout=60):
        req = urllib.request.Request(self.url + path, data=data, method=method, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()

    def get(self, path):
        return json.loads(self._req(path))

    def post(self, path, obj):
        return json.loads(self._req(path, json.dumps(obj).encode(), headers={'Content-Type': 'application/json'}) or b'{}')

    def alive(self):
        try:
            self.get('/system_stats')
            return True
        except Exception:
            return False

    def stats(self):
        s = self.get('/system_stats')
        dev = s.get('devices', [{}])[0]
        return {'vram_total': dev.get('vram_total', 0) / 2**30, 'vram_free': dev.get('vram_free', 0) / 2**30,
                'ram_free': s.get('system', {}).get('ram_free', 0) / 2**30}

    # -- files ---------------------------------------------------------------------------
    def upload(self, path, name=None, subfolder=''):
        """upload an image or video into ComfyUI/input, returns the name to reference"""
        name = name or os.path.basename(path)
        boundary = uuid.uuid4().hex
        ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        body = []
        for k, v in (('overwrite', 'true'), ('subfolder', subfolder), ('type', 'input')):
            body.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        body.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
                    f'Content-Type: {ctype}\r\n\r\n'.encode())
        body.append(open(path, 'rb').read())
        body.append(f'\r\n--{boundary}--\r\n'.encode())
        r = json.loads(self._req('/upload/image', b''.join(body),
                                 headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}, timeout=600))
        return (r.get('subfolder') + '/' if r.get('subfolder') else '') + r['name']

    def fetch(self, item, dst, move=False):
        """item = {'filename','subfolder','type'} from history outputs; move=True leaves no second copy
        in ComfyUI/output (disk is tight on the Mac)"""
        if self.root:
            src = os.path.join(self.root, item.get('type', 'output'), item.get('subfolder', ''), item['filename'])
            if os.path.exists(src):
                (shutil.move if move else shutil.copy)(src, dst)
                return dst
        q = urllib.parse.urlencode({'filename': item['filename'], 'subfolder': item.get('subfolder', ''),
                                    'type': item.get('type', 'output')})
        with open(dst, 'wb') as f:
            f.write(self._req('/view?' + q, timeout=600))
        return dst

    # -- execution -----------------------------------------------------------------------
    def submit(self, graph):
        try:
            r = self.post('/prompt', {'prompt': graph, 'client_id': self.client_id})
        except urllib.error.HTTPError as e:
            raise RuntimeError('ComfyUI rejected the graph: ' + e.read().decode()[:3000])
        return r['prompt_id']

    def wait(self, pid, timeout=6 * 3600, poll=2.0, on_tick=None):
        t0 = time.time()
        while time.time() - t0 < timeout:
            h = self.get(f'/history/{pid}')
            if pid in h:
                st = h[pid].get('status', {})
                if st.get('status_str') == 'error' or (st.get('completed') is False and st.get('messages')
                                                        and any(m[0] == 'execution_error' for m in st['messages'])):
                    msgs = [m for m in st.get('messages', []) if m[0] == 'execution_error']
                    raise RuntimeError('ComfyUI execution error: ' + json.dumps(msgs)[:3000])
                if (h[pid].get('outputs') and st.get('completed', True)) or st.get('status_str') == 'success':
                    return h[pid].get('outputs') or {}
            if on_tick:
                on_tick(time.time() - t0)
            time.sleep(poll)
        raise TimeoutError(pid)

    def run(self, graph, timeout=6 * 3600):
        return self.wait(self.submit(graph), timeout=timeout)

    def outputs(self, outs, kinds=('images', 'gifs', 'videos', 'video')):
        files = []
        for node in outs.values():
            for k in kinds:
                for it in node.get(k, []) or []:
                    if isinstance(it, dict) and 'filename' in it:
                        files.append(it)
        return files

    def stash_conditioning(self, names):
        """move output/conditioning/<name>_NNNNN_.safetensors -> models/embeddings/<name>.safetensors
        (so the video graphs can load prompts without the 4 GB text encoder in memory)"""
        if not self.root:
            raise RuntimeError('stash_conditioning needs the ComfyUI root')
        src_dir = os.path.join(self.root, 'output', 'conditioning')
        dst_dir = os.path.join(self.root, 'models', 'embeddings')
        os.makedirs(dst_dir, exist_ok=True)
        out = {}
        for n in names:
            cands = sorted(f for f in os.listdir(src_dir) if f.startswith(n + '_') and f.endswith('.safetensors'))
            if not cands:
                raise FileNotFoundError(f'no saved conditioning for {n} in {src_dir}')
            shutil.move(os.path.join(src_dir, cands[-1]), os.path.join(dst_dir, n + '.safetensors'))
            for f in cands[:-1]:
                os.remove(os.path.join(src_dir, f))
            out[n] = n + '.safetensors'
        return out

    def free(self, unload=True):
        """drop cached models from VRAM/RAM (between model families)"""
        try:
            self.post('/free', {'unload_models': unload, 'free_memory': True})
        except Exception:
            pass

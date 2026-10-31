"""Anime character mattes on CPU (skytnt anime-seg ISNet, ONNX), for print-style cut-outs.

  m = Matter()
  alpha = m(rgb_float)       # (H, W) float32 in [0, 1]
"""
import os

import cv2
import numpy as np

MODEL = os.environ.get('HW_SEG_MODEL', '/tmp/claude-0/models/seg/isnetis.onnx')


class Matter:
    def __init__(self, size=1024, threads=4):
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads
        self.sess = ort.InferenceSession(MODEL, so, providers=['CPUExecutionProvider'])
        self.inp = self.sess.get_inputs()[0].name
        self.size = size

    def __call__(self, rgb):
        h, w = rgb.shape[:2]
        s = self.size
        k = s / max(h, w)
        nh, nw = int(h * k), int(w * k)
        img = cv2.resize(rgb.astype(np.float32), (nw, nh), interpolation=cv2.INTER_AREA)
        pad = np.zeros((s, s, 3), np.float32)
        ph, pw = (s - nh) // 2, (s - nw) // 2
        pad[ph:ph + nh, pw:pw + nw] = img
        x = pad.transpose(2, 0, 1)[None]
        m = self.sess.run(None, {self.inp: x})[0][0, 0]
        m = m[ph:ph + nh, pw:pw + nw]
        return np.clip(cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR), 0, 1).astype(np.float32)

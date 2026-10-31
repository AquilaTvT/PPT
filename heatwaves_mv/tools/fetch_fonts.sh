#!/usr/bin/env bash
# Download the (SIL OFL) fonts the MV uses from the Google Fonts repository.
set -euo pipefail
mkdir -p "$(dirname "$0")/../assets/fonts"
cd "$(dirname "$0")/../assets/fonts"
B=https://raw.githubusercontent.com/google/fonts/main/ofl
for f in \
  shipporimincho/ShipporiMincho-ExtraBold.ttf shipporimincho/ShipporiMincho-SemiBold.ttf \
  shipporimincho/ShipporiMincho-Regular.ttf zenoldmincho/ZenOldMincho-Black.ttf zenoldmincho/ZenOldMincho-Bold.ttf \
  dotgothic16/DotGothic16-Regular.ttf delagothicone/DelaGothicOne-Regular.ttf yujisyuku/YujiSyuku-Regular.ttf \
  zenkakugothicnew/ZenKakuGothicNew-Black.ttf zenkakugothicnew/ZenKakuGothicNew-Medium.ttf \
  hinamincho/HinaMincho-Regular.ttf kleeone/KleeOne-SemiBold.ttf vt323/VT323-Regular.ttf \
  silkscreen/Silkscreen-Regular.ttf "ebgaramond/EBGaramond%5Bwght%5D.ttf" "ebgaramond/EBGaramond-Italic%5Bwght%5D.ttf" \
  "cormorantgaramond/CormorantGaramond-Italic%5Bwght%5D.ttf" "pixelifysans/PixelifySans%5Bwght%5D.ttf" \
  "notoserifsc/NotoSerifSC%5Bwght%5D.ttf"; do
  name=$(basename "$f" | sed 's/%5B/[/; s/%5D/]/')
  [ -s "$name" ] || curl -fsSL -o "$name" "$B/$f"
  echo "ok  $name"
done

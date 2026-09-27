# Country Holiday + Timezone Planner

나라·도시별 현지 시간, 공휴일, 겹치는 업무시간을 한 화면에서 보는 정적 웹사이트.
빌드 결과물은 `public/` 폴더이고, 그대로 Netlify·Vercel·GitHub Pages 등에 올리면 된다.

## 구조

| 경로 | 내용 |
|------|------|
| `site.config.json` | 도메인, 이메일, 애드센스 ID 등 **설정은 전부 여기** |
| `src/` | 스타일(`style.css`), 플래너 스크립트(`app.js`), 보조 스크립트(`site.js`), 가이드 글(`guides/*.html`) |
| `data/world.json` | 246개 나라, 473개 도시, 2025–2028 공휴일, 나라별 주말 |
| `scripts/gen_data.py` | `world.json` 생성 (python-holidays, babel) |
| `scripts/build.py` | 전체 페이지, `sitemap.xml`, `robots.txt`, `ads.txt` 생성 |
| `scripts/make_images.py` | 공유 이미지(`og.png`), 아이콘 생성 |
| `public/` | 배포되는 결과물 (빌드하면 덮어씀) |

## 빌드

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build.py
```

공휴일 데이터를 새로 받을 때만: `.venv/bin/python scripts/gen_data.py` 후 다시 build.

로컬 확인: `python3 -m http.server 8123 -d public` → http://localhost:8123

## 배포 전에 꼭 바꿀 것 (`site.config.json`)

1. `site_url` — 실제 도메인 (예: `https://worldtimeplanner.com`). 사이트맵, canonical, 공유 이미지 주소가 전부 이걸로 바뀐다.
2. `contact_email` — 실제로 받을 수 있는 이메일. 애드센스 심사에서 연락처를 본다.
3. `owner_name` — 운영자 이름이나 팀 이름 (About 페이지에 표시).
4. 바꾼 뒤 `scripts/build.py` 다시 실행.

## 애드센스 신청 순서

1. 도메인 연결 후 배포 (`git push origin main` → Netlify 자동 배포, publish 폴더 `public`).
2. [Google Search Console](https://search.google.com/search-console)에 사이트 등록 → `google_site_verification`에 인증 코드 넣고 다시 build·배포 → **Sitemaps 메뉴에 `sitemap.xml` 제출**.
3. 색인이 어느 정도 잡힌 뒤(보통 1–4주) 애드센스 신청.
4. 애드센스가 준 `ca-pub-...`를 `adsense_client`에 넣고 build·배포 → 모든 페이지 `<head>`에 광고 코드, 루트에 `ads.txt`가 자동 생성된다.
5. 애드센스 → 개인 정보 보호 및 메시지 → **유럽(EEA·영국·스위스) 동의 메시지** 켜기. 유럽 방문자에게 필요하다.

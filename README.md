# Simple Torrent Client

PySide6를 사용한 간단한 토렌트 클라이언트입니다.

## 기능

- 토렌트 파일 및 마그넷 링크 지원
- 실시간 다운로드/업로드 속도 표시
- 진행률 표시 및 토렌트 관리
- 일시정지/재개 기능
- 다크 테마 UI
- 전체 통계 표시

## 설치

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. libtorrent 설치 (macOS)

macOS에서는 Homebrew를 통해 libtorrent를 설치할 수 있습니다:

```bash
brew install libtorrent-rasterbar
pip install python-libtorrent
```

### 3. Python 패키지 설치 (대안)

pip를 통해 직접 설치할 수도 있습니다:

```bash
pip install PySide6 python-libtorrent requests
```

## 실행

```bash
python main.py
```

## 사용법

### 토렌트 파일 추가
1. "토렌트 파일 추가" 버튼을 클릭하거나 `Ctrl+O`를 누릅니다
2. `.torrent` 파일을 선택합니다
3. 다운로드할 폴더를 선택합니다

### 마그넷 링크 추가
1. "마그넷 링크 추가" 버튼을 클릭하거나 `Ctrl+M`을 누릅니다
2. 마그넷 링크를 입력합니다
3. 다운로드할 폴더를 선택합니다

### 토렌트 관리
- **일시정지**: 토렌트를 선택하고 "일시정지" 버튼을 클릭
- **재개**: 일시정지된 토렌트를 선택하고 "재개" 버튼을 클릭
- **제거**: 토렌트를 선택하고 "제거" 버튼을 클릭 (파일 삭제 여부 선택 가능)

### 단축키
- `Ctrl+O`: 토렌트 파일 추가
- `Ctrl+M`: 마그넷 링크 추가
- `Ctrl+Q`: 프로그램 종료

## 주의사항

1. **법적 책임**: 이 소프트웨어는 교육 목적으로 제작되었습니다. 저작권이 있는 콘텐츠의 불법 다운로드는 금지됩니다.

2. **방화벽 설정**: 토렌트 클라이언트가 정상적으로 작동하려면 포트 6881-6891이 열려있어야 합니다.

3. **네트워크**: 토렌트 다운로드는 네트워크 대역폭을 많이 사용할 수 있습니다.

## 문제 해결

### libtorrent 설치 오류
- macOS: `brew install libtorrent-rasterbar` 후 `pip install python-libtorrent`
- Ubuntu/Debian: `sudo apt-get install python3-libtorrent`
- Windows: `pip install python-libtorrent` (바이너리 패키지 사용)

### 권한 오류
다운로드 폴더에 쓰기 권한이 있는지 확인하세요.

### 포트 오류
다른 토렌트 클라이언트가 실행 중이면 포트 충돌이 발생할 수 있습니다.

## 라이센스

이 프로젝트는 교육 목적으로 제작되었습니다. 상업적 사용 시 관련 라이브러리의 라이센스를 확인하세요.

## 기여

버그 리포트나 기능 개선 제안은 언제든 환영합니다. 
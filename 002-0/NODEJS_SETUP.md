# Node.js 설치 가이드

YouTube Summary Agent의 React Frontend를 개발하기 위해서는 Node.js가 필요합니다.

## 🖥️ Windows 설치 (자세한 가이드)

### 1. Node.js 다운로드

1. 브라우저에서 [Node.js 공식 사이트](https://nodejs.org/) 방문
2. 메인 페이지에서 **LTS (Long Term Support)** 버전 선택
   - 권장: v20.x 이상
   - LTS 버전이 안정적이고 장기 지원됨

### 2. 설치 프로그램 실행

1. 다운로드한 `.msi` 파일 실행
2. 설치 마법사의 안내를 따라 진행:
   - ✅ "Add to PATH" 옵션 반드시 체크 (기본으로 체크되어 있음)
   - ✅ "Tools for Native Modules" 체크 (선택사항, 권장)
3. 설치 완료 후 컴퓨터 재시작 (선택사항, 권장)

### 3. 설치 확인

**명령 프롬프트 (CMD)** 또는 **PowerShell**을 열고:

```bash
node --version
```

출력 예시:
```
v20.10.0
```

```bash
npm --version
```

출력 예시:
```
10.2.3
```

### 4. 문제 해결

#### "node" 명령어를 찾을 수 없음

**해결방법 1: 환경 변수 확인**
1. Windows 검색에서 "환경 변수" 검색
2. "시스템 환경 변수 편집" 선택
3. "환경 변수" 버튼 클릭
4. "시스템 변수" 섹션에서 "Path" 찾기
5. 다음 경로가 있는지 확인:
   - `C:\Program Files\nodejs\`
6. 없으면 "새로 만들기"로 추가
7. 명령 프롬프트 재시작

**해결방법 2: 재설치**
1. "프로그램 추가/제거"에서 Node.js 완전 제거
2. 컴퓨터 재시작
3. Node.js 다시 설치

---

## 🍎 Mac 설치

### 방법 1: 공식 설치 프로그램 (권장)

1. [Node.js 공식 사이트](https://nodejs.org/) 방문
2. **LTS** 버전의 `.pkg` 파일 다운로드
3. 설치 프로그램 실행 및 지시 따르기
4. 설치 확인:
   ```bash
   node --version
   npm --version
   ```

### 방법 2: Homebrew 사용

```bash
# Homebrew 설치 (없는 경우)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Node.js 설치
brew install node

# 설치 확인
node --version
npm --version
```

---

## 🐧 Linux 설치

### Ubuntu/Debian

```bash
# NodeSource 저장소 추가 (최신 버전)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# Node.js 설치
sudo apt-get install -y nodejs

# 설치 확인
node --version
npm --version
```

### Fedora/CentOS/RHEL

```bash
# NodeSource 저장소 추가
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -

# Node.js 설치
sudo dnf install -y nodejs

# 설치 확인
node --version
npm --version
```

### Arch Linux

```bash
# Node.js 설치
sudo pacman -S nodejs npm

# 설치 확인
node --version
npm --version
```

---

## 🚀 설치 후 Frontend 셋업

### 1. React 앱 생성

```bash
# 프로젝트 루트 디렉토리로 이동
cd "C:\Users\asus\Documents\003. YouTubeSummaryAgent"

# React 앱 생성
npx create-react-app frontend
```

이 명령어는 다음을 수행합니다:
- `frontend` 폴더 생성
- React 및 필요한 패키지 설치
- 기본 React 앱 구조 생성

### 2. 필요한 패키지 설치

```bash
cd frontend

# Axios (API 통신) 및 React-Markdown (결과 표시) 설치
npm install axios react-markdown
```

### 3. 개발 서버 실행

```bash
npm start
```

브라우저가 자동으로 열리고 `http://localhost:3000`에서 React 앱을 확인할 수 있습니다.

---

## 📦 npm 기본 명령어

### 패키지 설치
```bash
npm install <package-name>        # 패키지 설치
npm install <package-name> --save # dependencies에 추가
npm install <package-name> --save-dev # devDependencies에 추가
```

### 패키지 제거
```bash
npm uninstall <package-name>      # 패키지 제거
```

### 프로젝트 실행
```bash
npm start          # 개발 서버 시작
npm run build      # 프로덕션 빌드
npm test           # 테스트 실행
```

### package.json 기반 설치
```bash
npm install        # package.json의 모든 패키지 설치
```

---

## 🔧 고급 설정 (선택사항)

### nvm (Node Version Manager) 사용

여러 버전의 Node.js를 관리하고 싶다면 nvm 사용을 권장합니다.

#### Windows: nvm-windows

1. [nvm-windows 릴리스 페이지](https://github.com/coreybutler/nvm-windows/releases) 방문
2. `nvm-setup.zip` 다운로드 및 설치
3. 사용법:
   ```bash
   nvm list available      # 설치 가능한 버전 목록
   nvm install 20.10.0     # 특정 버전 설치
   nvm use 20.10.0         # 특정 버전 사용
   nvm list                # 설치된 버전 목록
   ```

#### Mac/Linux: nvm

```bash
# nvm 설치
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# nvm 사용
nvm install 20          # Node.js 20 설치
nvm use 20              # Node.js 20 사용
nvm alias default 20    # 기본 버전 설정
```

---

## ❓ 자주 묻는 질문 (FAQ)

### Q1: npm install이 느려요
**A**: npm 캐시를 정리하고 재시도하세요:
```bash
npm cache clean --force
npm install
```

### Q2: EACCES 권한 오류 (Mac/Linux)
**A**: sudo 없이 npm을 사용하도록 설정:
```bash
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.profile
source ~/.profile
```

### Q3: Windows에서 PowerShell 스크립트 실행 오류
**A**: PowerShell 실행 정책 변경:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Q4: 어떤 버전을 설치해야 하나요?
**A**:
- **LTS (Long Term Support) 버전 권장** - 안정적이고 장기 지원
- 현재 권장: v20.x 이상
- 최신 기능이 필요한 경우: Current 버전

---

## 🔗 유용한 링크

- [Node.js 공식 사이트](https://nodejs.org/)
- [npm 공식 문서](https://docs.npmjs.com/)
- [nvm-windows GitHub](https://github.com/coreybutler/nvm-windows)
- [nvm GitHub](https://github.com/nvm-sh/nvm)
- [React 공식 문서](https://react.dev/)

---

**도움이 필요하면 README.md의 트러블슈팅 섹션을 참고하세요!**

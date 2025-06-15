# 사진 EXIF → Google My Maps 변환기

연속된 날짜 덩어리(chunk) 기반으로 사진의 EXIF 데이터를 처리하여 Google My Maps에 업로드할 수 있는 CSV/KML 파일을 생성하는 도구입니다.

## 🌟 주요 기능

- **자동 EXIF 데이터 추출**: 사진/영상 파일의 날짜, GPS 정보 자동 추출
- **연속 날짜 덩어리 탐지**: 연속된 날짜를 자동으로 그룹화 (예: 250511 → 5/11~5/13)
- **수동 보정 GUI**: 누락된 날짜/GPS 정보를 사용자 친화적인 GUI로 보정
- **다양한 내보내기 형식**: CSV, KML 파일 생성으로 Google My Maps 직접 업로드 가능
- **자동 순서 부여**: 같은 날짜 그룹 내에서 시간순 자동 정렬

## 📋 지원 파일 형식

- **이미지**: JPG, JPEG, PNG, HEIC, TIFF
- **영상**: MOV, MP4 (exiftool 필요)

## 🚀 설치 및 실행

### 1. 요구사항 설치

```bash
# Python 패키지 설치
pip install -r requirements.txt

# macOS에서 exiftool 설치 (영상 파일 처리용)
brew install exiftool
```

### 2. 실행

#### GUI 버전 (권장)

```bash
python main.py
```

#### CLI 버전 (tkinter 없는 환경)

```bash
# 대화형 모드
python cli_main.py

# 배치 모드
python cli_main.py -f "/path/to/photos"
python cli_main.py -f "/path/to/photos" -o csv
```

## 📖 사용 방법

### GUI 사용 (권장)

1. **사진 폴더 선택**: 처리할 사진들이 있는 폴더 선택
2. **EXIF 데이터 처리**: 자동으로 모든 사진의 메타데이터 추출 및 분석
3. **수동 보정** (선택사항): 누락된 정보를 GUI를 통해 보정
4. **파일 생성**: Google My Maps용 CSV/KML 파일 생성

### 프로그래밍 방식 사용

```python
from photo_exif_processor import PhotoExifProcessor
from data_exporter import DataExporter

# 1. EXIF 데이터 처리
processor = PhotoExifProcessor("/path/to/photos")
df = processor.process_all_photos()
processor.detect_date_chunks()
processor.add_order_column()

# 2. 결과 확인
print(processor.get_summary())

# 3. 파일 내보내기
exporter = DataExporter(processor)
results = exporter.export_all()
```

## 📊 워크플로우 상세

### 1단계: EXIF 스캔 & 파싱

- 지정된 폴더의 모든 이미지/영상 파일 검색
- `piexif` 라이브러리로 EXIF 데이터 추출
- 영상 파일은 `exiftool` 사용 (설치된 경우)

### 2단계: 연속 날짜 덩어리 탐지

```python
# 날짜별 그룹화 예시
df['date'] = pd.to_datetime(df['DateTimeOriginal']).dt.date
df = df.sort_values('date')
df['chunk'] = (df['date'].diff() > pd.Timedelta(days=1)).cumsum()
df['chunk_id'] = df.groupby('chunk')['date'].transform(
    lambda d: d.min().strftime('%y%m%d')
)
```

### 3단계: 데이터 분류

| 분류           | 조건                 | 처리 방식               |
| -------------- | -------------------- | ----------------------- |
| 자동 처리      | 날짜 + GPS 모두 있음 | 바로 내보내기           |
| 수동 날짜 보정 | GPS만 있음           | 날짜 입력 GUI           |
| 수동 GPS 보정  | 날짜만 있음          | 지도 클릭으로 좌표 입력 |
| 수동 전체 보정 | 둘 다 없음           | 날짜 + GPS 모두 입력    |

### 4단계: 수동 보정 GUI

- **사진 미리보기**: 현재 보정 중인 사진 표시
- **날짜 추정**: 앞뒤 사진 정보로 날짜 자동 추정
- **지도 연동**: Folium 지도로 GPS 좌표 시각적 선택

### 5단계: 파일 생성

#### CSV 파일 (Google My Maps 직접 업로드)

```csv
파일명,촬영일시,위도,경도,날짜그룹,순서
IMG_001.JPG,2025:05:11 09:28:00,37.566535,126.977969,250511,1
IMG_002.JPG,2025:05:11 09:28:05,37.566540,126.977975,250511,2
```

#### KML 파일 (Google Earth/My Maps)

- 날짜 그룹별 폴더 구조
- 순서별 색상 구분 (시작: 녹색, 끝: 빨간색, 중간: 파란색)
- 상세 정보 포함 (파일명, 촬영일시, 좌표, 순서)

## 📁 출력 파일 구조

```
output/
├── photo_exif_export_20250112_143022.csv      # 통합 CSV
├── photo_exif_export_20250112_143022.kml      # KML 파일
├── photo_exif_250511_20250112_143022.csv      # 날짜별 분리 CSV
├── photo_exif_250513_20250112_143022.csv      # 날짜별 분리 CSV
├── Google_My_Maps_업로드_가이드.txt             # 업로드 가이드
└── 내보내기_요약.txt                           # 처리 결과 요약
```

## 🗺️ Google My Maps 업로드 방법

### 방법 1: 통합 CSV 사용

1. [Google My Maps](https://mymaps.google.com) 접속
2. "새 지도 만들기" → "레이어 추가" → "가져오기"
3. `photo_exif_export_*.csv` 파일 선택
4. 위도/경도 컬럼 매핑: "위도", "경도" 선택
5. 제목 필드: "순서" 선택
6. "날짜그룹"으로 스타일 분류 설정

### 방법 2: 날짜별 분리 CSV 사용

1. 각 `photo_exif_[날짜그룹]_*.csv` 파일을 별도 레이어로 업로드
2. 레이어명을 날짜 그룹으로 설정
3. 각 레이어별 다른 색상/아이콘 적용

## 🔧 고급 사용법

### 원본 EXIF 덮어쓰기 (선택사항)

```python
# 보정된 데이터로 원본 파일 EXIF 업데이트
import subprocess

for _, row in df.iterrows():
    cmd = [
        'exiftool',
        f'-DateTimeOriginal={row["DateTimeOriginal"]}',
        f'-GPSLatitude={row["GPSLat"]}',
        f'-GPSLongitude={row["GPSLong"]}',
        '-overwrite_original',
        row['FilePath']
    ]
    subprocess.run(cmd)
```

### 커스텀 처리

```python
# 특정 날짜 범위만 처리
start_date = '2025-05-10'
end_date = '2025-05-15'
filtered_df = processor.df[
    (processor.df['datetime'] >= start_date) &
    (processor.df['datetime'] <= end_date)
]

# 커스텀 내보내기
exporter = DataExporter(processor)
exporter.processor.df = filtered_df  # 필터된 데이터 적용
custom_csv = exporter.export_csv('custom_export.csv')
```

## 🛠️ 문제 해결

### 자주 발생하는 문제

1. **exiftool not found**:

   ```bash
   # macOS
   brew install exiftool
   # Ubuntu/Debian
   sudo apt-get install exiftool
   ```

2. **PIL 이미지 로딩 실패**:

   - HEIC 파일: `pip install pillow-heif`
   - 권한 문제: 파일 읽기 권한 확인

3. **GUI 실행 오류 (tkinter 없음)**:

   ```bash
   # macOS (Homebrew로 Python 재설치)
   brew reinstall python-tk

   # Ubuntu/Debian
   sudo apt-get install python3-tk

   # 또는 CLI 버전 사용
   python cli_main.py
   ```

### 로그 확인

- 실행 로그: `photo_exif_log.txt`
- 상세 오류 정보 포함

## 📊 성능 참고사항

- **처리 속도**: 약 100-200장/분 (파일 크기 및 시스템 성능에 따라 다름)
- **메모리 사용량**: 사진 1000장당 약 50-100MB
- **Google My Maps 제한**: 레이어당 최대 2,000개 포인트, 파일 크기 5MB

## 🤝 기여하기

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이선스

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📧 문의

프로젝트에 대한 질문이나 제안이 있으시면 Issues를 통해 연락주세요.

---

**주의사항**:

- 사진의 개인정보를 고려하여 GPS 정보 공개 시 주의하세요
- 대량의 사진 처리 시 충분한 저장 공간을 확보하세요
- 원본 파일 백업을 권장합니다

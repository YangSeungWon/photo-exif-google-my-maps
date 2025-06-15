#!/usr/bin/env python3
"""
사진 EXIF → Google My Maps 변환기 (커맨드라인 버전)
tkinter가 없는 환경에서 사용할 수 있는 CLI 버전
"""

import sys
import os
from pathlib import Path
import logging
import argparse

# 로컬 모듈 import
from photo_exif_processor import PhotoExifProcessor
from data_exporter import DataExporter

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("photo_exif_log.txt", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """필요한 의존성 확인 (tkinter 제외)"""
    missing_modules = []

    try:
        import pandas
    except ImportError:
        missing_modules.append("pandas")

    try:
        import piexif
    except ImportError:
        missing_modules.append("piexif")

    try:
        from PIL import Image
    except ImportError:
        missing_modules.append("Pillow")

    try:
        import folium
    except ImportError:
        missing_modules.append("folium")

    try:
        import simplekml
    except ImportError:
        missing_modules.append("simplekml")

    if missing_modules:
        error_msg = f"""
필요한 Python 패키지가 설치되지 않았습니다:
{', '.join(missing_modules)}

다음 명령어로 설치해주세요:
pip install {' '.join(missing_modules)}

또는:
pip install -r requirements.txt
"""
        print(error_msg)
        sys.exit(1)


def interactive_mode():
    """대화형 모드"""
    print("=== 사진 EXIF → Google My Maps 변환기 (대화형 모드) ===")
    print()

    # 1. 폴더 선택
    while True:
        photo_folder = input(
            "사진 폴더 경로를 입력하세요 (또는 'quit' 입력하여 종료): "
        ).strip()

        if photo_folder.lower() == "quit":
            print("프로그램을 종료합니다.")
            return

        if photo_folder.startswith('"') and photo_folder.endswith('"'):
            photo_folder = photo_folder[1:-1]

        if photo_folder.startswith("'") and photo_folder.endswith("'"):
            photo_folder = photo_folder[1:-1]

        photo_path = Path(photo_folder)
        if photo_path.exists():
            break
        else:
            print(f"❌ 폴더가 존재하지 않습니다: {photo_folder}")
            print("다시 입력해주세요.")
            continue

    try:
        # 2. EXIF 데이터 처리
        print(f"\n📁 선택된 폴더: {photo_folder}")
        print("🔍 EXIF 데이터 처리를 시작합니다...")

        processor = PhotoExifProcessor(photo_folder)

        # 사진 스캔 및 EXIF 추출
        print("   📸 사진 파일 스캔 중...")
        df = processor.process_all_photos()
        print(f"   ✅ {len(df)}개 파일의 EXIF 데이터 추출 완료")

        if df.empty:
            print("❌ 처리할 사진이 없습니다.")
            return

        # 연속 날짜 덩어리 탐지
        print("   📅 연속 날짜 덩어리 탐지 중...")
        try:
            processor.detect_date_chunks()
            print("   ✅ 날짜 덩어리 탐지 완료")
        except Exception as e:
            print(f"   ⚠️ 날짜 덩어리 탐지 중 일부 오류: {e}")
            # 오류가 있어도 계속 진행

        # 순서 컬럼 추가
        processor.add_order_column()

        # 3. 처리 결과 요약
        print("\n📊 처리 결과 요약:")
        print(processor.get_summary())

        # 4. 분류 결과 표시
        auto_df, manual_date_df, manual_gps_df, manual_both_df = (
            processor.classify_processing_type()
        )

        if len(manual_date_df) + len(manual_gps_df) + len(manual_both_df) > 0:
            print("\n⚠️  수동 보정이 필요한 파일이 있습니다:")
            if len(manual_date_df) > 0:
                print(f"   📅 날짜만 없음: {len(manual_date_df)}개")
            if len(manual_gps_df) > 0:
                print(f"   🗺️  GPS만 없음: {len(manual_gps_df)}개")
            if len(manual_both_df) > 0:
                print(f"   ❌ 둘 다 없음: {len(manual_both_df)}개")

            print("\n현재 CLI 버전에서는 자동 처리가 가능한 파일만 내보냅니다.")
            print("수동 보정이 필요한 경우 GUI 버전을 사용하거나,")
            print("사진 파일의 EXIF 데이터를 먼저 정리해주세요.")

        # 5. 내보내기 옵션 선택
        print("\n📤 파일 내보내기 옵션:")
        print("1. 통합 CSV 파일")
        print("2. KML 파일")
        print("3. 모든 파일 (CSV + KML + 가이드)")
        print("4. 날짜별 분리 CSV 파일")

        while True:
            choice = input("\n선택 (1-4, 또는 'skip' 입력하여 건너뛰기): ").strip()

            if choice.lower() == "skip":
                print("내보내기를 건너뜁니다.")
                break

            try:
                choice_num = int(choice)
                if 1 <= choice_num <= 4:
                    export_files(processor, choice_num)
                    break
                else:
                    print("1-4 사이의 숫자를 입력해주세요.")
            except ValueError:
                print("올바른 숫자를 입력해주세요.")

        print("\n✅ 처리가 완료되었습니다!")

        # output 폴더 열기 제안
        if input("\n생성된 파일이 있는 폴더를 열까요? (y/N): ").lower() == "y":
            open_output_folder()

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        logger.error(f"처리 중 오류: {e}")


def export_files(processor, choice):
    """파일 내보내기"""
    try:
        exporter = DataExporter(processor)

        if choice == 1:
            print("📄 CSV 파일 생성 중...")
            csv_path = exporter.export_csv()
            print(f"✅ CSV 파일 생성 완료: {Path(csv_path).name}")

        elif choice == 2:
            print("🗺️ KML 파일 생성 중...")
            kml_path = exporter.export_kml()
            print(f"✅ KML 파일 생성 완료: {Path(kml_path).name}")

        elif choice == 3:
            print("📦 모든 파일 생성 중...")
            results = exporter.export_all()
            print("✅ 모든 파일 생성 완료!")
            print(f"   📄 통합 CSV: {Path(results['csv']).name}")
            print(f"   🗺️ KML 파일: {Path(results['kml']).name}")
            print(f"   📁 분리 CSV: {len(results['chunk_csvs'])}개 파일")
            print(f"   📖 업로드 가이드: {Path(results['guide']).name}")
            print(f"   📋 처리 요약: {Path(results['summary']).name}")

        elif choice == 4:
            print("📁 날짜별 분리 CSV 파일 생성 중...")
            csv_files = exporter.export_chunk_separated_csv()
            print(f"✅ 분리 CSV 파일 생성 완료: {len(csv_files)}개 파일")
            for csv_file in csv_files:
                print(f"   📄 {Path(csv_file).name}")

    except Exception as e:
        print(f"❌ 내보내기 중 오류: {e}")
        logger.error(f"내보내기 오류: {e}")


def open_output_folder():
    """output 폴더 열기"""
    output_path = Path("output").absolute()
    try:
        if sys.platform == "win32":
            os.startfile(output_path)
        elif sys.platform == "darwin":  # macOS
            os.system(f"open '{output_path}'")
        else:  # Linux
            os.system(f"xdg-open '{output_path}'")
        print(f"📂 폴더를 열었습니다: {output_path}")
    except Exception as e:
        print(f"⚠️ 폴더 열기 실패: {e}")
        print(f"📂 수동으로 확인하세요: {output_path}")


def batch_mode(photo_folder, output_format="all"):
    """배치 처리 모드"""
    print(f"=== 배치 처리 모드 ===")
    print(f"📁 처리 폴더: {photo_folder}")
    print(f"📤 출력 형식: {output_format}")

    try:
        processor = PhotoExifProcessor(photo_folder)

        # EXIF 데이터 처리
        df = processor.process_all_photos()
        processor.detect_date_chunks()
        processor.add_order_column()

        # 결과 요약
        print(processor.get_summary())

        # 파일 내보내기
        exporter = DataExporter(processor)

        if output_format == "csv":
            csv_path = exporter.export_csv()
            print(f"✅ CSV 생성: {csv_path}")
        elif output_format == "kml":
            kml_path = exporter.export_kml()
            print(f"✅ KML 생성: {kml_path}")
        elif output_format == "separated":
            csv_files = exporter.export_chunk_separated_csv()
            print(f"✅ 분리 CSV 생성: {len(csv_files)}개 파일")
        else:  # all
            results = exporter.export_all()
            print("✅ 모든 파일 생성 완료!")

    except Exception as e:
        print(f"❌ 배치 처리 오류: {e}")
        logger.error(f"배치 처리 오류: {e}")
        sys.exit(1)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="사진 EXIF → Google My Maps 변환기 (CLI 버전)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python cli_main.py                                    # 대화형 모드
  python cli_main.py -f "/path/to/photos"               # 배치 모드 (모든 파일)
  python cli_main.py -f "/path/to/photos" -o csv        # CSV만 생성
  python cli_main.py -f "/path/to/photos" -o kml        # KML만 생성
  python cli_main.py -f "/path/to/photos" -o separated  # 날짜별 분리 CSV

지원 파일 형식: JPG, JPEG, PNG, MOV, MP4, HEIC, TIFF
        """,
    )

    parser.add_argument("-f", "--folder", help="사진 폴더 경로")
    parser.add_argument(
        "-o",
        "--output",
        choices=["csv", "kml", "separated", "all"],
        default="all",
        help="출력 파일 형식 (기본값: all)",
    )
    parser.add_argument("--version", action="version", version="1.0.0")

    args = parser.parse_args()

    print("=== 사진 EXIF → Google My Maps 변환기 (CLI 버전) ===")
    print("GUI 버전이 필요한 경우 tkinter를 설치하고 main.py를 실행하세요.")
    print()

    # 의존성 확인
    print("🔍 의존성 확인 중...")
    check_dependencies()
    print("✅ 의존성 확인 완료")
    print()

    if args.folder:
        # 배치 모드
        folder_path = Path(args.folder)
        if not folder_path.exists():
            print(f"❌ 폴더가 존재하지 않습니다: {args.folder}")
            sys.exit(1)

        batch_mode(args.folder, args.output)
    else:
        # 대화형 모드
        interactive_mode()


if __name__ == "__main__":
    main()

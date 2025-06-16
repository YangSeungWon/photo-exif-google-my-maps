#!/usr/bin/env python3
"""
Manual Correction GUI for Photo EXIF Data
사진 날짜/GPS 수동 보정을 위한 GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import pandas as pd
from datetime import datetime
import webbrowser
import tempfile
import folium
import os
from pathlib import Path
import logging
import gc  # 가비지 컬렉션

logger = logging.getLogger(__name__)


class ManualCorrectionGUI:
    def __init__(self, processor):
        """
        수동 보정 GUI 초기화

        Args:
            processor: PhotoExifProcessor 인스턴스
        """
        self.processor = processor
        self.current_index = 0
        self.correction_data = []
        self.correction_type = None  # 'date', 'gps', 'both'

        self.root = tk.Tk()
        self.root.title("사진 EXIF 수동 보정")
        self.root.geometry("1200x800")

        self.setup_ui()

    def setup_ui(self):
        """UI 요소 설정"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 사진 미리보기 프레임
        self.photo_frame = ttk.LabelFrame(
            main_frame, text="사진 미리보기", padding="10"
        )
        self.photo_frame.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky=(tk.W, tk.E, tk.N, tk.S),
            padx=5,
            pady=5,
        )

        self.photo_label = ttk.Label(self.photo_frame)
        self.photo_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 이미지 참조 관리를 위한 변수 초기화
        self.current_photo = None
        self.photo_label.image = None

        # 파일 정보 프레임
        info_frame = ttk.LabelFrame(main_frame, text="파일 정보", padding="10")
        info_frame.grid(
            row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5
        )

        self.filename_label = ttk.Label(info_frame, text="파일명: -")
        self.filename_label.grid(row=0, column=0, sticky=tk.W, pady=2)

        self.filesize_label = ttk.Label(info_frame, text="파일 크기: -")
        self.filesize_label.grid(row=1, column=0, sticky=tk.W, pady=2)

        self.current_date_label = ttk.Label(info_frame, text="현재 날짜: -")
        self.current_date_label.grid(row=2, column=0, sticky=tk.W, pady=2)

        self.current_gps_label = ttk.Label(info_frame, text="현재 GPS: -")
        self.current_gps_label.grid(row=3, column=0, sticky=tk.W, pady=2)

        # 외부 뷰어로 열기 버튼
        self.open_external_button = ttk.Button(
            info_frame, text="외부 뷰어로 열기", command=self.open_external_viewer
        )
        self.open_external_button.grid(row=4, column=0, pady=10)

        # 보정 입력 프레임
        correction_frame = ttk.LabelFrame(main_frame, text="보정 입력", padding="10")
        correction_frame.grid(
            row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5
        )

        # 날짜 표시 (읽기 전용)
        ttk.Label(correction_frame, text="날짜:").grid(
            row=0, column=0, sticky=tk.W, pady=2
        )
        self.date_var = tk.StringVar()
        # 직접 수정 가능한 Entry
        self.date_entry = ttk.Entry(
            correction_frame,
            textvariable=self.date_var,
            width=22,
            font=("", 10, "bold"),
            foreground="blue",
        )
        self.date_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)
        ttk.Label(correction_frame, text="(YYYY:MM:DD HH:MM:SS)").grid(
            row=0, column=2, sticky=tk.W, pady=2
        )

        # 날짜 값을 설정하고 Entry를 동시에 업데이트하는 헬퍼
        def _set_date_value(value: str):
            """날짜 변수와 Entry를 함께 업데이트"""
            self.date_var.set(value)
            # Entry 텍스트도 동기화 (textvariable만으로 충분하지만 안전하게)
            if hasattr(self, "date_entry"):
                self.date_entry.delete(0, tk.END)
                self.date_entry.insert(0, value)

        # 인스턴스 메서드로 바인딩
        self.set_date_value = _set_date_value

        # 날짜 선택 버튼 프레임
        date_buttons_frame = ttk.LabelFrame(
            correction_frame, text="빠른 날짜 선택", padding="5"
        )
        date_buttons_frame.grid(
            row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10, padx=5
        )

        # 주변 사진 정보 표시
        self.prev_photo_label = ttk.Label(
            date_buttons_frame, text="이전 사진: -", font=("", 9)
        )
        self.prev_photo_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=2)

        self.next_photo_label = ttk.Label(
            date_buttons_frame, text="다음 사진: -", font=("", 9)
        )
        self.next_photo_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=2)

        # 날짜 선택 버튼들
        button_row = ttk.Frame(date_buttons_frame)
        button_row.grid(
            row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 5)
        )

        self.prev_plus_btn = ttk.Button(
            button_row, text="이전+1초", command=self.use_prev_plus_one, width=12
        )
        self.prev_plus_btn.grid(row=0, column=0, padx=2)

        self.middle_btn = ttk.Button(
            button_row, text="중간값", command=self.use_middle_time, width=12
        )
        self.middle_btn.grid(row=0, column=1, padx=2)

        self.next_minus_btn = ttk.Button(
            button_row, text="다음-1초", command=self.use_next_minus_one, width=12
        )
        self.next_minus_btn.grid(row=0, column=2, padx=2)

        # 포맷 예시 추가
        format_frame = ttk.Frame(correction_frame)
        format_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(format_frame, text="포맷 예시:", font=("", 9, "bold")).grid(
            row=0, column=0, sticky=tk.W
        )
        ttk.Label(
            format_frame, text="2024:03:15 14:30:25", font=("", 9), foreground="blue"
        ).grid(row=0, column=1, sticky=tk.W, padx=10)

        # GPS 입력
        ttk.Label(correction_frame, text="위도:").grid(
            row=3, column=0, sticky=tk.W, pady=2
        )
        self.lat_var = tk.StringVar()
        self.lat_entry = ttk.Entry(
            correction_frame, textvariable=self.lat_var, width=15
        )
        self.lat_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        ttk.Label(correction_frame, text="경도:").grid(
            row=4, column=0, sticky=tk.W, pady=2
        )
        self.lon_var = tk.StringVar()
        self.lon_entry = ttk.Entry(
            correction_frame, textvariable=self.lon_var, width=15
        )
        self.lon_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        # 지도 버튼
        self.map_button = ttk.Button(
            correction_frame, text="지도에서 선택", command=self.open_map_for_gps
        )
        self.map_button.grid(row=5, column=1, pady=10)

        # 진행 상황 프레임
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        self.progress_label = ttk.Label(progress_frame, text="진행 상황: 0/0")
        self.progress_label.grid(row=0, column=0, sticky=tk.W)

        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress_bar.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10)

        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        ttk.Button(button_frame, text="이전", command=self.prev_photo).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(button_frame, text="저장 & 다음", command=self.save_and_next).grid(
            row=0, column=1, padx=5
        )
        ttk.Button(button_frame, text="건너뛰기", command=self.skip_photo).grid(
            row=0, column=2, padx=5
        )
        ttk.Button(button_frame, text="완료", command=self.finish_correction).grid(
            row=0, column=3, padx=5
        )

        # 그리드 설정
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=2)
        main_frame.rowconfigure(1, weight=1)

        self.photo_frame.columnconfigure(0, weight=1)
        self.photo_frame.rowconfigure(0, weight=1)

        correction_frame.columnconfigure(1, weight=1)
        progress_frame.columnconfigure(1, weight=1)

    def start_correction(self, data, correction_type):
        """
        수동 보정 시작

        Args:
            data: 보정할 DataFrame
            correction_type: 'date', 'gps', 'both'
        """
        if data.empty:
            messagebox.showinfo("알림", "보정할 데이터가 없습니다.")
            return

        self.correction_data = data.copy()
        self.correction_type = correction_type
        self.current_index = 0

        self.progress_bar["maximum"] = len(self.correction_data)
        self.update_display()

        self.root.mainloop()

    def update_display(self):
        """현재 사진과 정보 표시 업데이트"""
        if self.current_index >= len(self.correction_data):
            return

        current_row = self.correction_data.iloc[self.current_index]

        # 파일 정보 업데이트
        file_path = current_row["FilePath"]
        self.current_file_path = file_path  # 외부 뷰어용으로 저장

        self.filename_label.config(text=f"파일명: {current_row['FileName']}")

        # 파일 크기 정보 추가
        try:
            file_size = os.path.getsize(file_path)
            if file_size > 1024 * 1024:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            elif file_size > 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size} bytes"
            self.filesize_label.config(text=f"파일 크기: {size_str}")
        except:
            self.filesize_label.config(text="파일 크기: 알 수 없음")

        self.current_date_label.config(
            text=f"현재 날짜: {current_row.get('DateTimeOriginal', '없음')}"
        )
        self.current_gps_label.config(
            text=f"현재 GPS: {current_row.get('GPSLat', '없음')}, {current_row.get('GPSLong', '없음')}"
        )

        # 진행 상황 업데이트
        self.progress_label.config(
            text=f"진행 상황: {self.current_index + 1}/{len(self.correction_data)}"
        )
        self.progress_bar["value"] = self.current_index + 1

        # 앞뒤 사진 타임스탬프 업데이트 (자동 날짜 입력 포함)
        self.update_surrounding_timestamps()

        # 입력 필드 초기화/설정 (자동 입력이 없는 경우에만)
        if self.correction_type in ["date", "both"]:
            current_date = current_row.get("DateTimeOriginal")
            # 이미 자동 입력된 값이 있으면 덮어쓰지 않음
            if pd.notna(current_date):
                self.set_date_value(current_date)
            elif not self.date_var.get().strip():
                # 자동 입력도 안되고 기존 값도 없으면 빈 값으로 설정
                self.set_date_value("")

        if self.correction_type in ["gps", "both"]:
            current_lat = current_row.get("GPSLat")
            current_lon = current_row.get("GPSLong")
            self.lat_var.set(str(current_lat) if pd.notna(current_lat) else "")
            self.lon_var.set(str(current_lon) if pd.notna(current_lon) else "")

        # 사진 미리보기 로드
        self.load_photo_preview(file_path)

    def update_surrounding_timestamps(self):
        """현재 사진 앞뒤 사진들의 타임스탬프 표시 및 자동 날짜 입력"""
        try:
            # UI 요소가 없으면 건너뛰기 (하지만 로그는 남기기)
            if not hasattr(self, "prev_photo_label") or not hasattr(
                self, "next_photo_label"
            ):
                logger.debug("UI 요소가 아직 생성되지 않음")
                return

            # 현재 파일 정보
            current_row = self.correction_data.iloc[self.current_index]
            current_file = current_row["FilePath"]
            current_filename = Path(current_file).name

            # 전체 데이터에서 날짜가 있는 파일들만 가져오기
            all_df = self.processor.df
            dated_df = all_df[all_df["DateTimeOriginal"].notna()].copy()

            if dated_df.empty:
                self.prev_photo_label.config(text="이전 사진: 날짜 정보 없음")
                self.next_photo_label.config(text="다음 사진: 날짜 정보 없음")
                return

            # 파일명 기준으로 정렬
            dated_df = dated_df.sort_values("FileName")

            # 현재 파일 앞뒤의 파일들 찾기
            prev_files = dated_df[dated_df["FileName"] < current_filename]
            next_files = dated_df[dated_df["FileName"] > current_filename]

            # 이전 사진 정보
            if not prev_files.empty:
                prev_file = prev_files.iloc[-1]  # 가장 가까운 이전 파일
                prev_date = prev_file["DateTimeOriginal"]
                prev_name = prev_file["FileName"]

                # IMG_xxx.jpg 형태의 파일명에서 번호 추출하여 표시
                if prev_name.upper().startswith("IMG_") and prev_name.upper().endswith(
                    (".JPG", ".JPEG")
                ):
                    try:
                        prev_num = (
                            prev_name.upper()
                            .replace("IMG_", "")
                            .replace(".JPG", "")
                            .replace(".JPEG", "")
                        )
                        prev_display = f"IMG_{prev_num}"
                    except:
                        prev_display = prev_name
                else:
                    prev_display = prev_name

                self.prev_photo_label.config(
                    text=f"이전 사진: {prev_display} → {prev_date}",
                    foreground="darkgreen",
                )

                # 버튼 활성화/비활성화 설정
                if hasattr(self, "prev_plus_btn"):
                    self.prev_plus_btn.config(state="normal")

            else:
                if hasattr(self, "prev_photo_label"):
                    self.prev_photo_label.config(
                        text="이전 사진: 없음", foreground="gray"
                    )
                # 이전 사진이 없으면 이전+1초 버튼 비활성화
                if hasattr(self, "prev_plus_btn"):
                    self.prev_plus_btn.config(state="disabled")

            # 다음 사진 정보
            if not next_files.empty:
                next_file = next_files.iloc[0]  # 가장 가까운 다음 파일
                next_date = next_file["DateTimeOriginal"]
                next_name = next_file["FileName"]

                # IMG_xxx.jpg 형태의 파일명에서 번호 추출하여 표시
                if next_name.upper().startswith("IMG_") and next_name.upper().endswith(
                    (".JPG", ".JPEG")
                ):
                    try:
                        next_num = (
                            next_name.upper()
                            .replace("IMG_", "")
                            .replace(".JPG", "")
                            .replace(".JPEG", "")
                        )
                        next_display = f"IMG_{next_num}"
                    except:
                        next_display = next_name
                else:
                    next_display = next_name

                self.next_photo_label.config(
                    text=f"다음 사진: {next_display} → {next_date}",
                    foreground="darkblue",
                )
                # 다음 사진이 있으면 다음-1초 버튼 활성화
                if hasattr(self, "next_minus_btn"):
                    self.next_minus_btn.config(state="normal")
            else:
                if hasattr(self, "next_photo_label"):
                    self.next_photo_label.config(
                        text="다음 사진: 없음", foreground="gray"
                    )
                # 다음 사진이 없으면 다음-1초 버튼 비활성화
                if hasattr(self, "next_minus_btn"):
                    self.next_minus_btn.config(state="disabled")

            # 중간값 버튼은 앞뒤 모두 있을 때만 활성화
            if hasattr(self, "middle_btn"):
                if not prev_files.empty and not next_files.empty:
                    self.middle_btn.config(state="normal")
                else:
                    self.middle_btn.config(state="disabled")

        except Exception as e:
            logger.warning(f"앞뒤 사진 타임스탬프 업데이트 중 오류: {e}")
            if hasattr(self, "prev_photo_label"):
                self.prev_photo_label.config(text="이전 사진: 오류")
            if hasattr(self, "next_photo_label"):
                self.next_photo_label.config(text="다음 사진: 오류")

    def use_prev_plus_one(self):
        """이전 사진 + 1초 사용"""
        try:
            current_row = self.correction_data.iloc[self.current_index]
            current_filename = Path(current_row["FilePath"]).name

            # 전체 데이터에서 날짜가 있는 파일들만 가져오기
            all_df = self.processor.df
            dated_df = all_df[all_df["DateTimeOriginal"].notna()].copy()
            dated_df = dated_df.sort_values("FileName")

            # 이전 파일 찾기
            prev_files = dated_df[dated_df["FileName"] < current_filename]

            if not prev_files.empty:
                prev_file = prev_files.iloc[-1]
                prev_date = prev_file["DateTimeOriginal"]

                # 안전한 날짜 파싱 및 1초 추가
                if isinstance(prev_date, str):
                    from datetime import datetime

                    prev_dt = datetime.strptime(prev_date, "%Y:%m:%d %H:%M:%S")
                    suggested_dt = prev_dt.replace(second=prev_dt.second + 1)
                    suggested_date = suggested_dt.strftime("%Y:%m:%d %H:%M:%S")
                else:
                    prev_dt = pd.to_datetime(prev_date)
                    suggested_dt = prev_dt + pd.Timedelta(seconds=1)
                    suggested_date = suggested_dt.strftime("%Y:%m:%d %H:%M:%S")

                self.set_date_value(suggested_date)
                # UI 강제 업데이트 (여러 방법 시도)
                self.date_entry.delete(0, tk.END)
                self.date_entry.insert(0, suggested_date)
                self.date_entry.update_idletasks()
                self.root.update_idletasks()
                logger.info(f"이전+1초 적용: {suggested_date}")
            else:
                messagebox.showwarning("알림", "이전 사진이 없습니다.")

        except Exception as e:
            logger.error(f"이전+1초 적용 중 오류: {e}")
            messagebox.showerror("오류", f"이전+1초 적용 중 오류가 발생했습니다:\n{e}")

    def use_middle_time(self):
        """앞뒤 사진의 중간값 사용"""
        try:
            current_row = self.correction_data.iloc[self.current_index]
            current_filename = Path(current_row["FilePath"]).name

            # 전체 데이터에서 날짜가 있는 파일들만 가져오기
            all_df = self.processor.df
            dated_df = all_df[all_df["DateTimeOriginal"].notna()].copy()
            dated_df = dated_df.sort_values("FileName")

            # 앞뒤 파일 찾기
            prev_files = dated_df[dated_df["FileName"] < current_filename]
            next_files = dated_df[dated_df["FileName"] > current_filename]

            if not prev_files.empty and not next_files.empty:
                prev_file = prev_files.iloc[-1]
                next_file = next_files.iloc[0]
                prev_date = prev_file["DateTimeOriginal"]
                next_date = next_file["DateTimeOriginal"]

                # 안전한 날짜 파싱 및 중간값 계산
                from datetime import datetime

                if isinstance(prev_date, str):
                    prev_dt = datetime.strptime(prev_date, "%Y:%m:%d %H:%M:%S")
                else:
                    prev_dt = pd.to_datetime(prev_date).to_pydatetime()

                if isinstance(next_date, str):
                    next_dt = datetime.strptime(next_date, "%Y:%m:%d %H:%M:%S")
                else:
                    next_dt = pd.to_datetime(next_date).to_pydatetime()

                # 중간값 계산
                time_diff = next_dt - prev_dt
                middle_dt = prev_dt + time_diff / 2
                suggested_date = middle_dt.strftime("%Y:%m:%d %H:%M:%S")

                self.set_date_value(suggested_date)
                # UI 강제 업데이트 (여러 방법 시도)
                self.date_entry.delete(0, tk.END)
                self.date_entry.insert(0, suggested_date)
                self.date_entry.update_idletasks()
                self.root.update_idletasks()
                logger.info(f"중간값 적용: {suggested_date}")
            else:
                messagebox.showwarning("알림", "앞뒤 사진이 모두 필요합니다.")

        except Exception as e:
            logger.error(f"중간값 적용 중 오류: {e}")
            messagebox.showerror("오류", f"중간값 적용 중 오류가 발생했습니다:\n{e}")

    def use_next_minus_one(self):
        """다음 사진 - 1초 사용"""
        try:
            current_row = self.correction_data.iloc[self.current_index]
            current_filename = Path(current_row["FilePath"]).name

            # 전체 데이터에서 날짜가 있는 파일들만 가져오기
            all_df = self.processor.df
            dated_df = all_df[all_df["DateTimeOriginal"].notna()].copy()
            dated_df = dated_df.sort_values("FileName")

            # 다음 파일 찾기
            next_files = dated_df[dated_df["FileName"] > current_filename]

            if not next_files.empty:
                next_file = next_files.iloc[0]
                next_date = next_file["DateTimeOriginal"]

                # 안전한 날짜 파싱 및 1초 빼기
                if isinstance(next_date, str):
                    from datetime import datetime

                    next_dt = datetime.strptime(next_date, "%Y:%m:%d %H:%M:%S")
                    suggested_dt = next_dt.replace(second=next_dt.second - 1)
                    suggested_date = suggested_dt.strftime("%Y:%m:%d %H:%M:%S")
                else:
                    next_dt = pd.to_datetime(next_date)
                    suggested_dt = next_dt - pd.Timedelta(seconds=1)
                    suggested_date = suggested_dt.strftime("%Y:%m:%d %H:%M:%S")

                self.set_date_value(suggested_date)
                # UI 강제 업데이트 (여러 방법 시도)
                self.date_entry.delete(0, tk.END)
                self.date_entry.insert(0, suggested_date)
                self.date_entry.update_idletasks()
                self.root.update_idletasks()
                logger.info(f"다음-1초 적용: {suggested_date}")
            else:
                messagebox.showwarning("알림", "다음 사진이 없습니다.")

        except Exception as e:
            logger.error(f"다음-1초 적용 중 오류: {e}")
            messagebox.showerror("오류", f"다음-1초 적용 중 오류가 발생했습니다:\n{e}")

    def load_photo_preview(self, file_path):
        """사진 미리보기 로드"""
        try:
            # 파일 존재 확인
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

            # 파일 확장자 확인
            file_ext = Path(file_path).suffix.lower()
            supported_formats = {
                ".jpg",
                ".jpeg",
                ".png",
                ".bmp",
                ".gif",
                ".tiff",
                ".tif",
            }

            if file_ext not in supported_formats:
                # 지원하지 않는 형식의 경우 기본 아이콘 표시
                self.show_file_icon(file_path)
                return

            # 이미지 로드
            try:
                image = Image.open(file_path)

                # 이미지 크기 체크 (너무 큰 이미지는 미리 거부)
                width, height = image.size
                if width * height > 50_000_000:  # 5천만 픽셀 이상
                    logger.warning(f"이미지가 너무 큼: {width}x{height}")
                    raise Exception(f"이미지가 너무 큽니다 ({width}x{height})")

                # RGBA 모드로 변환 (투명도 지원)
                if image.mode in ("RGBA", "LA"):
                    # 투명 배경을 흰색으로 변환
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    if image.mode == "RGBA":
                        background.paste(image, mask=image.split()[-1])
                    else:
                        background.paste(image, mask=image.split()[-1])
                    image = background
                elif image.mode != "RGB":
                    image = image.convert("RGB")

            except Exception as img_error:
                logger.warning(f"이미지 로드 실패 {file_path}: {img_error}")
                self.show_file_icon(file_path)
                return

            # 미리보기 크기 계산 (메모리 절약을 위해 더 작게)
            max_width, max_height = 300, 225  # 4:3 비율로 더 작게

            # 원본이 너무 큰 경우 먼저 크기 줄이기
            if image.size[0] > 2000 or image.size[1] > 2000:
                # 큰 이미지는 먼저 절반으로 줄이기
                temp_size = (image.size[0] // 2, image.size[1] // 2)
                image = image.resize(temp_size, Image.NEAREST)  # 빠른 리사이즈

            # 호환성을 위해 다양한 리샘플링 방법 시도
            try:
                # Pillow 10.0.0+ 방식
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            except AttributeError:
                try:
                    # Pillow 9.x 방식
                    image.thumbnail((max_width, max_height), Image.LANCZOS)
                except AttributeError:
                    # 구버전 Pillow 방식
                    image.thumbnail((max_width, max_height), Image.ANTIALIAS)

            # Tkinter PhotoImage로 변환 (여러 방법 시도)
            photo = None

            # 방법 1: 직접 PhotoImage 생성
            try:
                photo = ImageTk.PhotoImage(image)
            except Exception as e1:
                logger.warning(f"PhotoImage 생성 실패 (방법 1): {e1}")

                # 방법 2: 임시 파일로 저장 후 로드
                try:
                    import tempfile

                    with tempfile.NamedTemporaryFile(
                        suffix=".png", delete=False
                    ) as tmp_file:
                        image.save(tmp_file.name, "PNG")
                        photo = tk.PhotoImage(file=tmp_file.name)
                        os.unlink(tmp_file.name)  # 임시 파일 삭제
                except Exception as e2:
                    logger.warning(f"PhotoImage 생성 실패 (방법 2): {e2}")

                    # 방법 3: 메모리 버퍼 사용
                    try:
                        import io

                        buffer = io.BytesIO()
                        image.save(buffer, format="PNG")
                        buffer.seek(0)
                        photo = tk.PhotoImage(data=buffer.getvalue())
                    except Exception as e3:
                        logger.warning(f"PhotoImage 생성 실패 (방법 3): {e3}")
                        raise Exception("모든 PhotoImage 생성 방법 실패")

            if photo:
                # 기존 이미지 참조 정리
                self.clear_current_image()

                # 새 이미지 설정
                self.photo_label.config(image=photo, text="")
                self.current_photo = photo  # 클래스 변수에 참조 저장
                self.photo_label.image = photo  # 라벨에도 참조 저장 (이중 보호)

                logger.info(f"미리보기 로드 성공: {Path(file_path).name}")
            else:
                raise Exception("PhotoImage 생성 실패")

        except Exception as e:
            logger.warning(f"사진 미리보기 로드 실패 {file_path}: {e}")
            self.show_error_preview(file_path, str(e))

    def clear_current_image(self):
        """현재 이미지 참조 정리"""
        try:
            if hasattr(self, "current_photo") and self.current_photo:
                del self.current_photo
                self.current_photo = None

            if hasattr(self.photo_label, "image") and self.photo_label.image:
                del self.photo_label.image
                self.photo_label.image = None

            # 가비지 컬렉션 강제 실행
            gc.collect()

        except Exception as e:
            logger.warning(f"이미지 참조 정리 중 오류: {e}")

    def show_file_icon(self, file_path):
        """지원하지 않는 파일 형식에 대한 아이콘 표시"""
        try:
            file_ext = Path(file_path).suffix.lower()
            file_name = Path(file_path).name

            # 파일 형식별 아이콘 선택
            if file_ext in {".mov", ".mp4", ".avi", ".mkv"}:
                icon = "🎬"
                type_name = "동영상 파일"
            elif file_ext in {".heic", ".heif"}:
                icon = "📷"
                type_name = "HEIC 이미지"
            elif file_ext in {".raw", ".cr2", ".nef", ".arw"}:
                icon = "📸"
                type_name = "RAW 이미지"
            else:
                icon = "📁"
                type_name = "지원하지 않는 형식"

            # 파일 정보 포함한 아이콘 텍스트
            try:
                file_size = os.path.getsize(file_path)
                if file_size > 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.1f}MB"
                else:
                    size_str = f"{file_size / 1024:.1f}KB"
            except:
                size_str = "크기 불명"

            icon_text = f"{icon}\n{file_name}\n\n{type_name}\n({file_ext})\n{size_str}\n\n'외부 뷰어로 열기' 버튼을\n사용해주세요"

            self.clear_current_image()
            self.photo_label.config(image="", text=icon_text)

        except Exception as e:
            logger.warning(f"파일 아이콘 표시 실패 {file_path}: {e}")
            self.show_error_preview(file_path, str(e))

    def show_error_preview(self, file_path, error_msg):
        """에러 발생 시 표시할 미리보기"""
        try:
            file_name = Path(file_path).name if file_path else "알 수 없는 파일"
            error_text = f"❌\n{file_name}\n\n미리보기 로드 실패\n\n오류: {error_msg[:50]}{'...' if len(error_msg) > 50 else ''}"

            self.clear_current_image()
            self.photo_label.config(image="", text=error_text)

        except Exception:
            self.clear_current_image()
            self.photo_label.config(image="", text="❌\n미리보기를\n불러올 수 없습니다")

    def open_external_viewer(self):
        """외부 이미지 뷰어로 현재 파일 열기"""
        if not hasattr(self, "current_file_path") or not self.current_file_path:
            messagebox.showwarning("경고", "열 파일이 선택되지 않았습니다.")
            return

        try:
            file_path = self.current_file_path

            if not os.path.exists(file_path):
                messagebox.showerror("오류", f"파일을 찾을 수 없습니다:\n{file_path}")
                return

            # 운영체제별 기본 뷰어로 열기
            import subprocess
            import sys

            if sys.platform == "win32":
                # Windows
                os.startfile(file_path)
            elif sys.platform == "darwin":
                # macOS
                subprocess.run(["open", file_path])
            else:
                # Linux
                subprocess.run(["xdg-open", file_path])

            logger.info(f"외부 뷰어로 파일 열기: {Path(file_path).name}")

        except Exception as e:
            error_msg = f"외부 뷰어로 파일을 열 수 없습니다:\n{e}"
            logger.error(f"외부 뷰어 열기 실패 {file_path}: {e}")
            messagebox.showerror("오류", error_msg)

    def prev_photo(self):
        """이전 사진으로 이동"""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()

    def save_and_next(self):
        """현재 입력 저장하고 다음 사진으로"""
        if self.validate_and_save():
            self.next_photo()

    def skip_photo(self):
        """현재 사진 건너뛰고 다음으로"""
        self.next_photo()

    def next_photo(self):
        """다음 사진으로 이동"""
        self.current_index += 1
        if self.current_index >= len(self.correction_data):
            self.finish_correction()
        else:
            self.update_display()

    def validate_and_save(self):
        """입력 데이터 검증 및 저장"""
        try:
            current_idx = self.correction_data.index[self.current_index]

            # 날짜 검증 및 저장
            if self.correction_type in ["date", "both"]:
                date_str = self.date_var.get().strip()
                if date_str:
                    # 날짜 형식 검증
                    datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    self.correction_data.loc[current_idx, "DateTimeOriginal"] = date_str

            # GPS 검증 및 저장
            if self.correction_type in ["gps", "both"]:
                lat_str = self.lat_var.get().strip()
                lon_str = self.lon_var.get().strip()

                if lat_str and lon_str:
                    lat = float(lat_str)
                    lon = float(lon_str)

                    # GPS 범위 검증
                    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                        raise ValueError("GPS 좌표 범위가 올바르지 않습니다")

                    self.correction_data.loc[current_idx, "GPSLat"] = lat
                    self.correction_data.loc[current_idx, "GPSLong"] = lon

            return True

        except ValueError as e:
            messagebox.showerror("입력 오류", f"입력 형식이 올바르지 않습니다:\n{e}")
            return False
        except Exception as e:
            messagebox.showerror("오류", f"저장 중 오류가 발생했습니다:\n{e}")
            return False

    def open_map_for_gps(self):
        """지도를 열어서 GPS 좌표 선택"""
        if self.correction_type not in ["gps", "both"]:
            return

        try:
            # 현재 위치 또는 기본 위치 (서울) 설정
            center_lat = 37.5665
            center_lon = 126.9780

            # 현재 GPS가 있으면 그 위치를 중심으로
            if self.lat_var.get() and self.lon_var.get():
                try:
                    center_lat = float(self.lat_var.get())
                    center_lon = float(self.lon_var.get())
                except:
                    pass

            # 주변 사진들의 GPS 위치를 마커로 표시
            m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

            # 현재 청크의 다른 사진들 위치 표시
            current_row = self.correction_data.iloc[self.current_index]
            current_chunk = current_row.get("chunk_id")

            if pd.notna(current_chunk):
                chunk_df = self.processor.df[
                    (self.processor.df["chunk_id"] == current_chunk)
                    & (self.processor.df["GPSLat"].notna())
                    & (self.processor.df["GPSLong"].notna())
                ]

                for _, row in chunk_df.iterrows():
                    folium.Marker(
                        [row["GPSLat"], row["GPSLong"]],
                        popup=row["FileName"],
                        icon=folium.Icon(color="blue", icon="camera"),
                    ).add_to(m)

            # 임시 HTML 파일로 저장
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            m.save(temp_file.name)
            temp_file.close()

            # 브라우저에서 열기
            webbrowser.open("file://" + temp_file.name)

            # GPS 입력 다이얼로그
            self.show_gps_input_dialog()

        except Exception as e:
            messagebox.showerror("오류", f"지도 열기 중 오류가 발생했습니다:\n{e}")

    def show_gps_input_dialog(self):
        """GPS 좌표 입력 다이얼로그"""
        dialog = tk.Toplevel(self.root)
        dialog.title("GPS 좌표 입력")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="지도에서 확인한 좌표를 입력하세요:").pack(pady=10)

        frame = ttk.Frame(dialog)
        frame.pack(pady=10)

        ttk.Label(frame, text="위도:").grid(row=0, column=0, padx=5, pady=5)
        lat_entry = ttk.Entry(frame, width=15)
        lat_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="경도:").grid(row=1, column=0, padx=5, pady=5)
        lon_entry = ttk.Entry(frame, width=15)
        lon_entry.grid(row=1, column=1, padx=5, pady=5)

        def apply_coordinates():
            try:
                lat = float(lat_entry.get())
                lon = float(lon_entry.get())
                self.lat_var.set(str(lat))
                self.lon_var.set(str(lon))
                dialog.destroy()
            except ValueError:
                messagebox.showerror("오류", "올바른 숫자를 입력해주세요.")

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="적용", command=apply_coordinates).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="취소", command=dialog.destroy).pack(
            side=tk.LEFT, padx=5
        )

    def finish_correction(self):
        """보정 완료"""
        try:
            # 보정된 데이터를 원본 processor에 반영
            if not self.correction_data.empty:
                for idx, row in self.correction_data.iterrows():
                    # processor의 df에서 해당 행 찾아서 업데이트
                    mask = self.processor.df["FilePath"] == row["FilePath"]

                    if self.correction_type in ["date", "both"] and pd.notna(
                        row["DateTimeOriginal"]
                    ):
                        self.processor.df.loc[mask, "DateTimeOriginal"] = row[
                            "DateTimeOriginal"
                        ]

                    if self.correction_type in ["gps", "both"]:
                        if pd.notna(row["GPSLat"]):
                            self.processor.df.loc[mask, "GPSLat"] = row["GPSLat"]
                        if pd.notna(row["GPSLong"]):
                            self.processor.df.loc[mask, "GPSLong"] = row["GPSLong"]

            messagebox.showinfo("완료", "수동 보정이 완료되었습니다.")
            self.root.destroy()

        except Exception as e:
            messagebox.showerror("오류", f"보정 완료 중 오류가 발생했습니다:\n{e}")


def show_correction_menu(processor):
    """단계별 보정 메뉴 표시"""
    auto_df, manual_date_df, manual_gps_df, manual_both_df = (
        processor.classify_processing_type()
    )

    # 단계별 보정 필요 파일 계산
    step1_files = (
        pd.concat([manual_date_df, manual_both_df])
        if not manual_date_df.empty or not manual_both_df.empty
        else pd.DataFrame()
    )
    step2_files = (
        pd.concat([manual_gps_df, manual_both_df])
        if not manual_gps_df.empty or not manual_both_df.empty
        else pd.DataFrame()
    )

    root = tk.Tk()
    root.title("단계별 수동 보정")
    root.geometry("500x400")

    ttk.Label(root, text="단계별 수동 보정", font=("", 14, "bold")).pack(pady=20)

    # 단계 설명
    info_frame = ttk.Frame(root)
    info_frame.pack(pady=10, padx=20, fill="x")

    step1_text = f"""📅 1단계: 시간 보정 → {len(step1_files)}개 파일
• GPS는 있지만 날짜 없음: {len(manual_date_df)}개
• 날짜와 GPS 둘 다 없음: {len(manual_both_df)}개"""

    step2_text = f"""🗺️ 2단계: 장소 보정 → {len(step2_files)}개 파일  
• 날짜는 있지만 GPS 없음: {len(manual_gps_df)}개
• 1단계 완료 후 GPS 입력 필요: {len(manual_both_df)}개"""

    ttk.Label(info_frame, text=step1_text, justify=tk.LEFT, font=("", 10)).pack(
        anchor="w", pady=5
    )
    ttk.Label(info_frame, text=step2_text, justify=tk.LEFT, font=("", 10)).pack(
        anchor="w", pady=5
    )

    # 추천 순서 안내
    ttk.Label(
        root,
        text="💡 권장: 1단계 → 2단계 순서로 진행",
        font=("", 11),
        foreground="blue",
    ).pack(pady=10)

    # 버튼 프레임
    button_frame = ttk.Frame(root)
    button_frame.pack(pady=20)

    def start_step1_correction():
        root.destroy()
        if not step1_files.empty:
            gui = ManualCorrectionGUI(processor)
            gui.start_correction(step1_files, "date")
        else:
            messagebox.showinfo("알림", "1단계 시간 보정이 필요한 파일이 없습니다.")

    def start_step2_correction():
        root.destroy()
        if not step2_files.empty:
            gui = ManualCorrectionGUI(processor)
            gui.start_correction(step2_files, "gps")
        else:
            messagebox.showinfo("알림", "2단계 장소 보정이 필요한 파일이 없습니다.")

    # 1단계 버튼
    step1_btn = ttk.Button(
        button_frame, text="1단계: 시간 보정", command=start_step1_correction
    )
    step1_btn.pack(pady=8, ipadx=20)
    if len(step1_files) == 0:
        step1_btn.config(state="disabled")
        step1_btn.config(text="✅ 1단계: 시간 보정 완료")

    # 2단계 버튼
    step2_btn = ttk.Button(
        button_frame, text="2단계: 장소 보정", command=start_step2_correction
    )
    step2_btn.pack(pady=8, ipadx=20)
    if len(step2_files) == 0:
        step2_btn.config(state="disabled")
        step2_btn.config(text="✅ 2단계: 장소 보정 완료")

    # 취소 버튼
    ttk.Button(button_frame, text="취소", command=root.destroy).pack(pady=15)

    # 진행 상황 표시
    if len(step1_files) == 0 and len(step2_files) == 0:
        ttk.Label(
            root,
            text="🎉 모든 보정이 완료되었습니다!",
            font=("", 12),
            foreground="green",
        ).pack(pady=10)

    root.mainloop()

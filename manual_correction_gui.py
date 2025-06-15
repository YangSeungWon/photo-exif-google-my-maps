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

        # 파일 정보 프레임
        info_frame = ttk.LabelFrame(main_frame, text="파일 정보", padding="10")
        info_frame.grid(
            row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5
        )

        self.filename_label = ttk.Label(info_frame, text="파일명: -")
        self.filename_label.grid(row=0, column=0, sticky=tk.W, pady=2)

        self.current_date_label = ttk.Label(info_frame, text="현재 날짜: -")
        self.current_date_label.grid(row=1, column=0, sticky=tk.W, pady=2)

        self.current_gps_label = ttk.Label(info_frame, text="현재 GPS: -")
        self.current_gps_label.grid(row=2, column=0, sticky=tk.W, pady=2)

        # 보정 입력 프레임
        correction_frame = ttk.LabelFrame(main_frame, text="보정 입력", padding="10")
        correction_frame.grid(
            row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5
        )

        # 날짜 입력
        ttk.Label(correction_frame, text="날짜:").grid(
            row=0, column=0, sticky=tk.W, pady=2
        )
        self.date_var = tk.StringVar()
        self.date_entry = ttk.Entry(
            correction_frame, textvariable=self.date_var, width=20
        )
        self.date_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)
        ttk.Label(correction_frame, text="(YYYY:MM:DD HH:MM:SS)").grid(
            row=0, column=2, sticky=tk.W, pady=2
        )

        # GPS 입력
        ttk.Label(correction_frame, text="위도:").grid(
            row=1, column=0, sticky=tk.W, pady=2
        )
        self.lat_var = tk.StringVar()
        self.lat_entry = ttk.Entry(
            correction_frame, textvariable=self.lat_var, width=15
        )
        self.lat_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        ttk.Label(correction_frame, text="경도:").grid(
            row=2, column=0, sticky=tk.W, pady=2
        )
        self.lon_var = tk.StringVar()
        self.lon_entry = ttk.Entry(
            correction_frame, textvariable=self.lon_var, width=15
        )
        self.lon_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)

        # 지도 버튼
        self.map_button = ttk.Button(
            correction_frame, text="지도에서 선택", command=self.open_map_for_gps
        )
        self.map_button.grid(row=3, column=1, pady=10)

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

        # 자동 날짜 추정 버튼
        ttk.Button(button_frame, text="날짜 추정", command=self.estimate_date).grid(
            row=0, column=4, padx=5
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
        self.filename_label.config(text=f"파일명: {current_row['FileName']}")
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

        # 입력 필드 초기화/설정
        if self.correction_type in ["date", "both"]:
            current_date = current_row.get("DateTimeOriginal")
            self.date_var.set(current_date if pd.notna(current_date) else "")

        if self.correction_type in ["gps", "both"]:
            current_lat = current_row.get("GPSLat")
            current_lon = current_row.get("GPSLong")
            self.lat_var.set(str(current_lat) if pd.notna(current_lat) else "")
            self.lon_var.set(str(current_lon) if pd.notna(current_lon) else "")

        # 사진 미리보기 로드
        self.load_photo_preview(current_row["FilePath"])

    def load_photo_preview(self, file_path):
        """사진 미리보기 로드"""
        try:
            # 이미지 로드 및 리사이즈
            image = Image.open(file_path)

            # 미리보기 크기 계산 (최대 400x300 유지하면서 비율 유지)
            max_width, max_height = 400, 300
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # Tkinter PhotoImage로 변환
            photo = ImageTk.PhotoImage(image)
            self.photo_label.config(image=photo)
            self.photo_label.image = photo  # 참조 유지

        except Exception as e:
            logger.warning(f"사진 미리보기 로드 실패 {file_path}: {e}")
            self.photo_label.config(image="", text="미리보기를 불러올 수 없습니다")

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

    def estimate_date(self):
        """주변 사진 날짜를 기반으로 날짜 추정"""
        if self.correction_type not in ["date", "both"]:
            return

        try:
            # 이전/다음 사진의 날짜 정보 찾기
            current_file = self.correction_data.iloc[self.current_index]["FilePath"]
            all_df = self.processor.df

            # 파일명 기준으로 정렬된 주변 사진들의 날짜 찾기
            file_df = all_df[all_df["DateTimeOriginal"].notna()].copy()
            file_df = file_df.sort_values("FileName")

            current_filename = Path(current_file).name

            # 현재 파일 앞뒤의 날짜가 있는 파일들 찾기
            prev_dates = file_df[file_df["FileName"] < current_filename][
                "DateTimeOriginal"
            ]
            next_dates = file_df[file_df["FileName"] > current_filename][
                "DateTimeOriginal"
            ]

            estimated_date = None

            if not prev_dates.empty and not next_dates.empty:
                # 앞뒤 날짜의 중간값 계산
                prev_dt = pd.to_datetime(prev_dates.iloc[-1])
                next_dt = pd.to_datetime(next_dates.iloc[0])
                estimated_date = prev_dt + (next_dt - prev_dt) / 2

            elif not prev_dates.empty:
                # 이전 날짜 + 1분
                prev_dt = pd.to_datetime(prev_dates.iloc[-1])
                estimated_date = prev_dt + pd.Timedelta(minutes=1)

            elif not next_dates.empty:
                # 다음 날짜 - 1분
                next_dt = pd.to_datetime(next_dates.iloc[0])
                estimated_date = next_dt - pd.Timedelta(minutes=1)

            if estimated_date:
                formatted_date = estimated_date.strftime("%Y:%m:%d %H:%M:%S")
                self.date_var.set(formatted_date)
                messagebox.showinfo("날짜 추정", f"추정된 날짜: {formatted_date}")
            else:
                messagebox.showinfo(
                    "날짜 추정", "주변 사진에서 날짜 정보를 찾을 수 없습니다."
                )

        except Exception as e:
            messagebox.showerror("오류", f"날짜 추정 중 오류가 발생했습니다:\n{e}")

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
    """보정 유형 선택 메뉴 표시"""
    auto_df, manual_date_df, manual_gps_df, manual_both_df = (
        processor.classify_processing_type()
    )

    root = tk.Tk()
    root.title("수동 보정 선택")
    root.geometry("400x300")

    ttk.Label(root, text="수동 보정할 항목을 선택하세요:", font=("", 12)).pack(pady=20)

    info_text = f"""
보정 가능한 항목:
• 날짜만 없음: {len(manual_date_df)}개
• GPS만 없음: {len(manual_gps_df)}개  
• 둘 다 없음: {len(manual_both_df)}개
    """

    ttk.Label(root, text=info_text, justify=tk.LEFT).pack(pady=10)

    def start_date_correction():
        root.destroy()
        if not manual_date_df.empty:
            gui = ManualCorrectionGUI(processor)
            gui.start_correction(manual_date_df, "date")
        else:
            messagebox.showinfo("알림", "날짜 보정이 필요한 파일이 없습니다.")

    def start_gps_correction():
        root.destroy()
        if not manual_gps_df.empty:
            gui = ManualCorrectionGUI(processor)
            gui.start_correction(manual_gps_df, "gps")
        else:
            messagebox.showinfo("알림", "GPS 보정이 필요한 파일이 없습니다.")

    def start_both_correction():
        root.destroy()
        if not manual_both_df.empty:
            gui = ManualCorrectionGUI(processor)
            gui.start_correction(manual_both_df, "both")
        else:
            messagebox.showinfo("알림", "전체 보정이 필요한 파일이 없습니다.")

    ttk.Button(root, text="날짜 보정", command=start_date_correction).pack(pady=5)
    ttk.Button(root, text="GPS 보정", command=start_gps_correction).pack(pady=5)
    ttk.Button(root, text="전체 보정", command=start_both_correction).pack(pady=5)
    ttk.Button(root, text="취소", command=root.destroy).pack(pady=5)

    root.mainloop()

import sys
import os
import subprocess
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                               QWidget, QPushButton, QTableWidget, QTableWidgetItem,
                               QFileDialog, QInputDialog, QMessageBox, QProgressBar,
                               QLabel, QHeaderView, QMenu, QMenuBar, QStatusBar,
                               QSplitter, QGroupBox, QGridLayout, QLineEdit, QSpinBox,
                               QCheckBox, QSlider, QTextEdit, QTabWidget, QComboBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QFont
from torrent_client import TorrentClient


class TorrentMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Torrent Client")
        self.setGeometry(100, 100, 1000, 700)
        
        # 토렌트 클라이언트 초기화
        self.torrent_client = TorrentClient()
        self.torrent_client.torrent_added.connect(self.on_torrent_added)
        self.torrent_client.progress_updated.connect(self.on_progress_updated)
        self.torrent_client.torrent_finished.connect(self.on_torrent_finished)
        self.torrent_client.security_alert.connect(self.on_security_alert)
        
        # UI 설정
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        
        # 토렌트 데이터 저장
        self.torrent_rows = {}  # hash -> row 매핑
        
        # 자동 종료 옵션
        self.auto_shutdown_enabled = False
        
        # 업데이트 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.check_auto_shutdown)
        self.update_timer.start(5000)  # 5초마다 확인
        
        # Tor 상태 확인 타이머
        self.tor_check_timer = QTimer()
        self.tor_check_timer.timeout.connect(self.check_tor_status)
        self.tor_check_timer.start(10000)  # 10초마다 Tor 상태 확인
        self.check_tor_status()  # 시작 시 한 번 확인
        
    def setup_ui(self):
        """UI 구성"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        
        # 툴바 버튼들
        toolbar_layout = QHBoxLayout()
        
        self.add_torrent_btn = QPushButton("토렌트 파일 추가")
        self.add_torrent_btn.clicked.connect(self.add_torrent_file)
        
        self.add_magnet_btn = QPushButton("마그넷 링크 추가")
        self.add_magnet_btn.clicked.connect(self.add_magnet_link)
        
        self.pause_btn = QPushButton("일시정지")
        self.pause_btn.clicked.connect(self.pause_selected)
        
        self.resume_btn = QPushButton("재개")
        self.resume_btn.clicked.connect(self.resume_selected)
        
        self.remove_btn = QPushButton("제거")
        self.remove_btn.clicked.connect(self.remove_selected)
        
        toolbar_layout.addWidget(self.add_torrent_btn)
        toolbar_layout.addWidget(self.add_magnet_btn)
        toolbar_layout.addWidget(self.pause_btn)
        toolbar_layout.addWidget(self.resume_btn)
        toolbar_layout.addWidget(self.remove_btn)
        toolbar_layout.addStretch()
        
        main_layout.addLayout(toolbar_layout)
        
        # 스플리터로 상하 분할
        splitter = QSplitter(Qt.Vertical)
        
        # 토렌트 테이블
        self.torrent_table = QTableWidget()
        self.torrent_table.setColumnCount(7)
        self.torrent_table.setHorizontalHeaderLabels([
            "이름", "진행률", "다운로드 속도", "업로드 속도", "시드", "피어", "상태"
        ])
        
        # 헤더 설정
        header = self.torrent_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 이름 컬럼 확장
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        
        self.torrent_table.setColumnWidth(1, 100)  # 진행률
        self.torrent_table.setColumnWidth(2, 120)  # 다운로드 속도
        self.torrent_table.setColumnWidth(3, 120)  # 업로드 속도
        self.torrent_table.setColumnWidth(4, 60)   # 시드
        self.torrent_table.setColumnWidth(5, 60)   # 피어
        self.torrent_table.setColumnWidth(6, 100)  # 상태
        
        self.torrent_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.torrent_table.setAlternatingRowColors(True)
        
        splitter.addWidget(self.torrent_table)
        
        # 정보 패널 (탭으로 구성)
        info_widget = QTabWidget()
        
        # 통계 탭
        stats_tab = QWidget()
        stats_tab_layout = QGridLayout(stats_tab)
        
        # 전체 통계
        stats_group = QGroupBox("전체 통계")
        stats_group_layout = QGridLayout(stats_group)
        
        self.total_down_label = QLabel("총 다운로드: 0 B/s")
        self.total_up_label = QLabel("총 업로드: 0 B/s")
        self.active_torrents_label = QLabel("활성 토렌트: 0")
        
        stats_group_layout.addWidget(self.total_down_label, 0, 0)
        stats_group_layout.addWidget(self.total_up_label, 0, 1)
        stats_group_layout.addWidget(self.active_torrents_label, 1, 0)
        
        stats_tab_layout.addWidget(stats_group, 0, 0)
        
        # 속도 제한 컨트롤
        speed_control_group = QGroupBox("속도 제한")
        speed_layout = QGridLayout(speed_control_group)
        
        # 업로드 속도 제한
        speed_layout.addWidget(QLabel("업로드 제한 (KB/s):"), 0, 0)
        self.upload_limit_spinbox = QSpinBox()
        self.upload_limit_spinbox.setRange(0, 99999)
        self.upload_limit_spinbox.setValue(0)
        self.upload_limit_spinbox.setSpecialValueText("무제한")
        self.upload_limit_spinbox.valueChanged.connect(self.on_upload_limit_changed)
        speed_layout.addWidget(self.upload_limit_spinbox, 0, 1)
        
        # 다운로드 속도 제한
        speed_layout.addWidget(QLabel("다운로드 제한 (KB/s):"), 1, 0)
        self.download_limit_spinbox = QSpinBox()
        self.download_limit_spinbox.setRange(0, 99999)
        self.download_limit_spinbox.setValue(0)
        self.download_limit_spinbox.setSpecialValueText("무제한")
        self.download_limit_spinbox.valueChanged.connect(self.on_download_limit_changed)
        speed_layout.addWidget(self.download_limit_spinbox, 1, 1)
        
        stats_tab_layout.addWidget(speed_control_group, 0, 1)
        
        # 자동 종료 옵션
        shutdown_group = QGroupBox("자동 종료")
        shutdown_layout = QVBoxLayout(shutdown_group)
        
        self.auto_shutdown_checkbox = QCheckBox("모든 다운로드 완료 시 컴퓨터 종료")
        self.auto_shutdown_checkbox.toggled.connect(self.on_auto_shutdown_toggled)
        shutdown_layout.addWidget(self.auto_shutdown_checkbox)
        
        stats_tab_layout.addWidget(shutdown_group, 1, 0, 1, 2)
        
        # 통계 탭 추가
        info_widget.addTab(stats_tab, "통계 & 설정")
        
        # 보안 탭
        security_tab = QWidget()
        security_layout = QGridLayout(security_tab)
        
        # 보안 설정
        security_settings_group = QGroupBox("보안 설정")
        security_settings_layout = QGridLayout(security_settings_group)
        
        # 암호화 설정
        self.encryption_checkbox = QCheckBox("피어 간 통신 암호화")
        self.encryption_checkbox.setChecked(True)
        self.encryption_checkbox.toggled.connect(self.on_encryption_toggled)
        security_settings_layout.addWidget(self.encryption_checkbox, 0, 0)
        
        # DHT 설정
        self.dht_checkbox = QCheckBox("DHT 사용 (비활성화 시 익명성 향상)")
        self.dht_checkbox.setChecked(True)
        self.dht_checkbox.toggled.connect(self.on_dht_toggled)
        security_settings_layout.addWidget(self.dht_checkbox, 1, 0)
        
        # IP 차단 입력
        security_settings_layout.addWidget(QLabel("IP 주소 차단:"), 2, 0)
        self.block_ip_input = QLineEdit()
        self.block_ip_input.setPlaceholderText("예: 192.168.1.100")
        security_settings_layout.addWidget(self.block_ip_input, 2, 1)
        
        self.block_ip_button = QPushButton("차단 추가")
        self.block_ip_button.clicked.connect(self.on_block_ip_clicked)
        security_settings_layout.addWidget(self.block_ip_button, 2, 2)
        
        security_layout.addWidget(security_settings_group, 0, 0)
        
        # 익명성 설정
        anonymity_group = QGroupBox("익명성 & 프록시 설정")
        anonymity_layout = QGridLayout(anonymity_group)
        
        # 익명 모드
        self.anonymous_checkbox = QCheckBox("익명 모드 (DHT/LSD 비활성화, User-Agent 변경)")
        self.anonymous_checkbox.toggled.connect(self.on_anonymous_toggled)
        anonymity_layout.addWidget(self.anonymous_checkbox, 0, 0, 1, 3)
        
        # 프록시 설정
        anonymity_layout.addWidget(QLabel("프록시 타입:"), 1, 0)
        self.proxy_type_combo = QComboBox()
        self.proxy_type_combo.addItems(["없음", "HTTP", "SOCKS4", "SOCKS5", "HTTP (인증)", "SOCKS5 (인증)"])
        self.proxy_type_combo.currentTextChanged.connect(self.on_proxy_type_changed)
        anonymity_layout.addWidget(self.proxy_type_combo, 1, 1, 1, 2)
        
        # 프록시 호스트
        anonymity_layout.addWidget(QLabel("프록시 주소:"), 2, 0)
        self.proxy_host_input = QLineEdit()
        self.proxy_host_input.setPlaceholderText("예: 127.0.0.1")
        self.proxy_host_input.setEnabled(False)
        anonymity_layout.addWidget(self.proxy_host_input, 2, 1)
        
        # 프록시 포트
        anonymity_layout.addWidget(QLabel("포트:"), 2, 2)
        self.proxy_port_input = QLineEdit()
        self.proxy_port_input.setPlaceholderText("예: 1080")
        self.proxy_port_input.setEnabled(False)
        anonymity_layout.addWidget(self.proxy_port_input, 2, 3)
        
        # 프록시 인증 (처음에는 숨김)
        self.proxy_username_label = QLabel("사용자명:")
        self.proxy_username_input = QLineEdit()
        self.proxy_username_input.setEnabled(False)
        self.proxy_password_label = QLabel("비밀번호:")
        self.proxy_password_input = QLineEdit()
        self.proxy_password_input.setEchoMode(QLineEdit.Password)
        self.proxy_password_input.setEnabled(False)
        
        anonymity_layout.addWidget(self.proxy_username_label, 3, 0)
        anonymity_layout.addWidget(self.proxy_username_input, 3, 1)
        anonymity_layout.addWidget(self.proxy_password_label, 3, 2)
        anonymity_layout.addWidget(self.proxy_password_input, 3, 3)
        
        # 프록시 인증 필드 숨기기
        self.proxy_username_label.hide()
        self.proxy_username_input.hide()
        self.proxy_password_label.hide()
        self.proxy_password_input.hide()
        
        # 프록시 설정 버튼
        self.proxy_apply_button = QPushButton("프록시 적용")
        self.proxy_apply_button.clicked.connect(self.on_proxy_apply_clicked)
        self.proxy_apply_button.setEnabled(False)
        anonymity_layout.addWidget(self.proxy_apply_button, 4, 0)
        
        self.proxy_disable_button = QPushButton("프록시 비활성화")
        self.proxy_disable_button.clicked.connect(self.on_proxy_disable_clicked)
        self.proxy_disable_button.setEnabled(False)
        anonymity_layout.addWidget(self.proxy_disable_button, 4, 1)
        
        # Tor 자동 연결 버튼
        self.tor_connect_button = QPushButton("🧅 Tor 자동 연결")
        self.tor_connect_button.clicked.connect(self.on_tor_connect_clicked)
        anonymity_layout.addWidget(self.tor_connect_button, 4, 2)
        
        # Tor 상태 표시
        self.tor_status_label = QLabel("Tor: 연결 안됨")
        anonymity_layout.addWidget(self.tor_status_label, 5, 0, 1, 3)
        
        security_layout.addWidget(anonymity_group, 0, 1)
        
        # 보안 통계
        security_stats_group = QGroupBox("보안 통계")
        security_stats_layout = QGridLayout(security_stats_group)
        
        self.encryption_status_label = QLabel("암호화: 활성화")
        self.dht_status_label = QLabel("DHT: 활성화")
        self.anonymity_status_label = QLabel("익명 모드: 비활성화")
        self.proxy_status_label = QLabel("프록시: 비활성화")
        self.blocked_ips_count_label = QLabel("차단된 IP: 0개")
        self.security_events_count_label = QLabel("보안 이벤트: 0개")
        
        security_stats_layout.addWidget(self.encryption_status_label, 0, 0)
        security_stats_layout.addWidget(self.dht_status_label, 0, 1)
        security_stats_layout.addWidget(self.anonymity_status_label, 1, 0)
        security_stats_layout.addWidget(self.proxy_status_label, 1, 1)
        security_stats_layout.addWidget(self.blocked_ips_count_label, 2, 0)
        security_stats_layout.addWidget(self.security_events_count_label, 2, 1)
        
        security_layout.addWidget(security_stats_group, 1, 0, 1, 2)
        
        # 보안 로그
        security_log_group = QGroupBox("보안 로그")
        security_log_layout = QVBoxLayout(security_log_group)
        
        self.security_log_text = QTextEdit()
        self.security_log_text.setMaximumHeight(150)
        self.security_log_text.setReadOnly(True)
        security_log_layout.addWidget(self.security_log_text)
        
        # 로그 제어 버튼
        log_buttons_layout = QHBoxLayout()
        self.refresh_log_button = QPushButton("로그 새로고침")
        self.refresh_log_button.clicked.connect(self.refresh_security_log)
        self.clear_log_button = QPushButton("로그 지우기")
        self.clear_log_button.clicked.connect(self.clear_security_log)
        
        log_buttons_layout.addWidget(self.refresh_log_button)
        log_buttons_layout.addWidget(self.clear_log_button)
        log_buttons_layout.addStretch()
        
        security_log_layout.addLayout(log_buttons_layout)
        security_layout.addWidget(security_log_group, 2, 0, 1, 2)
        
        # 보안 탭 추가
        info_widget.addTab(security_tab, "보안")
        
        splitter.addWidget(info_widget)
        splitter.setStretchFactor(0, 3)  # 테이블이 더 큰 공간 차지
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
    def setup_menu(self):
        """메뉴바 설정"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu('파일')
        
        add_torrent_action = QAction('토렌트 파일 추가...', self)
        add_torrent_action.setShortcut('Ctrl+O')
        add_torrent_action.triggered.connect(self.add_torrent_file)
        file_menu.addAction(add_torrent_action)
        
        add_magnet_action = QAction('마그넷 링크 추가...', self)
        add_magnet_action.setShortcut('Ctrl+M')
        add_magnet_action.triggered.connect(self.add_magnet_link)
        file_menu.addAction(add_magnet_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('종료', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 토렌트 메뉴
        torrent_menu = menubar.addMenu('토렌트')
        
        pause_action = QAction('일시정지', self)
        pause_action.triggered.connect(self.pause_selected)
        torrent_menu.addAction(pause_action)
        
        resume_action = QAction('재개', self)
        resume_action.triggered.connect(self.resume_selected)
        torrent_menu.addAction(resume_action)
        
        remove_action = QAction('제거', self)
        remove_action.triggered.connect(self.remove_selected)
        torrent_menu.addAction(remove_action)
        
    def setup_status_bar(self):
        """상태바 설정"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("준비")
        
    def add_torrent_file(self):
        """토렌트 파일 추가"""
        file_dialog = QFileDialog()
        torrent_file, _ = file_dialog.getOpenFileName(
            self, "토렌트 파일 선택", "", "Torrent Files (*.torrent)"
        )
        
        if torrent_file:
            # 다운로드 경로 선택
            download_path = QFileDialog.getExistingDirectory(
                self, "다운로드 경로 선택", os.path.expanduser("~/Downloads")
            )
            
            if download_path:
                torrent_hash = self.torrent_client.add_torrent(torrent_file, download_path)
                if torrent_hash:
                    self.status_bar.showMessage(f"토렌트가 추가되었습니다: {os.path.basename(torrent_file)}")
                else:
                    QMessageBox.warning(self, "오류", "토렌트 파일을 추가할 수 없습니다.")
    
    def add_magnet_link(self):
        """마그넷 링크 추가"""
        magnet_uri, ok = QInputDialog.getText(
            self, "마그넷 링크 추가", "마그넷 링크를 입력하세요:"
        )
        
        if ok and magnet_uri:
            # 다운로드 경로 선택
            download_path = QFileDialog.getExistingDirectory(
                self, "다운로드 경로 선택", os.path.expanduser("~/Downloads")
            )
            
            if download_path:
                torrent_hash = self.torrent_client.add_magnet_link(magnet_uri, download_path)
                if torrent_hash:
                    self.status_bar.showMessage("마그넷 링크가 추가되었습니다.")
                else:
                    QMessageBox.warning(self, "오류", "마그넷 링크를 추가할 수 없습니다.")
    
    def pause_selected(self):
        """선택된 토렌트 일시정지"""
        current_row = self.torrent_table.currentRow()
        if current_row >= 0:
            torrent_hash = self.get_torrent_hash_from_row(current_row)
            if torrent_hash:
                self.torrent_client.pause_torrent(torrent_hash)
    
    def resume_selected(self):
        """선택된 토렌트 재개"""
        current_row = self.torrent_table.currentRow()
        if current_row >= 0:
            torrent_hash = self.get_torrent_hash_from_row(current_row)
            if torrent_hash:
                self.torrent_client.resume_torrent(torrent_hash)
    
    def remove_selected(self):
        """선택된 토렌트 제거"""
        current_row = self.torrent_table.currentRow()
        if current_row >= 0:
            torrent_hash = self.get_torrent_hash_from_row(current_row)
            if torrent_hash:
                reply = QMessageBox.question(
                    self, "토렌트 제거", 
                    "토렌트를 제거하시겠습니까?\n\n파일도 함께 삭제하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                
                if reply == QMessageBox.Yes:
                    self.torrent_client.remove_torrent(torrent_hash, True)
                elif reply == QMessageBox.No:
                    self.torrent_client.remove_torrent(torrent_hash, False)
                
                if reply != QMessageBox.Cancel:
                    self.torrent_table.removeRow(current_row)
                    # 행 매핑 업데이트
                    for hash_key, row in list(self.torrent_rows.items()):
                        if row == current_row:
                            del self.torrent_rows[hash_key]
                        elif row > current_row:
                            self.torrent_rows[hash_key] = row - 1
    
    def get_torrent_hash_from_row(self, row):
        """행 번호로부터 토렌트 해시 얻기"""
        for torrent_hash, torrent_row in self.torrent_rows.items():
            if torrent_row == row:
                return torrent_hash
        return None
    
    def format_bytes(self, bytes_value):
        """바이트를 읽기 쉬운 형태로 변환"""
        if bytes_value == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        
        while bytes_value >= 1024 and unit_index < len(units) - 1:
            bytes_value /= 1024
            unit_index += 1
        
        return f"{bytes_value:.1f} {units[unit_index]}"
    
    def on_torrent_added(self, torrent_hash, name):
        """토렌트 추가 시 호출"""
        row = self.torrent_table.rowCount()
        self.torrent_table.insertRow(row)
        
        # 토렌트 정보 추가
        self.torrent_table.setItem(row, 0, QTableWidgetItem(name))
        self.torrent_table.setItem(row, 1, QTableWidgetItem("0%"))
        self.torrent_table.setItem(row, 2, QTableWidgetItem("0 B/s"))
        self.torrent_table.setItem(row, 3, QTableWidgetItem("0 B/s"))
        self.torrent_table.setItem(row, 4, QTableWidgetItem("0"))
        self.torrent_table.setItem(row, 5, QTableWidgetItem("0"))
        self.torrent_table.setItem(row, 6, QTableWidgetItem("대기중"))
        
        # 진행률 바 추가
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        self.torrent_table.setCellWidget(row, 1, progress_bar)
        
        self.torrent_rows[torrent_hash] = row
    
    def on_progress_updated(self, torrent_hash, progress, down_rate, up_rate, seeds, peers):
        """진행률 업데이트 시 호출"""
        if torrent_hash in self.torrent_rows:
            row = self.torrent_rows[torrent_hash]
            
            # 진행률 업데이트
            progress_bar = self.torrent_table.cellWidget(row, 1)
            if progress_bar:
                progress_bar.setValue(int(progress * 100))
            
            # 속도 및 기타 정보 업데이트
            self.torrent_table.setItem(row, 2, QTableWidgetItem(f"{self.format_bytes(down_rate)}/s"))
            self.torrent_table.setItem(row, 3, QTableWidgetItem(f"{self.format_bytes(up_rate)}/s"))
            self.torrent_table.setItem(row, 4, QTableWidgetItem(str(seeds)))
            self.torrent_table.setItem(row, 5, QTableWidgetItem(str(peers)))
            
            # 상태 업데이트
            if progress >= 1.0:
                self.torrent_table.setItem(row, 6, QTableWidgetItem("완료"))
            elif down_rate > 0:
                self.torrent_table.setItem(row, 6, QTableWidgetItem("다운로드중"))
            else:
                self.torrent_table.setItem(row, 6, QTableWidgetItem("대기중"))
        
        self.update_statistics()
    
    def on_torrent_finished(self, torrent_hash):
        """토렌트 완료 시 호출"""
        if torrent_hash in self.torrent_rows:
            row = self.torrent_rows[torrent_hash]
            self.torrent_table.setItem(row, 6, QTableWidgetItem("완료"))
            
        self.status_bar.showMessage("토렌트 다운로드가 완료되었습니다!")
    
    def update_statistics(self):
        """전체 통계 업데이트"""
        total_down = 0
        total_up = 0
        active_count = 0
        
        for torrent_hash in self.torrent_rows.keys():
            status = self.torrent_client.get_torrent_status(torrent_hash)
            if status:
                total_down += status['download_rate']
                total_up += status['upload_rate']
                if status['download_rate'] > 0 or status['upload_rate'] > 0:
                    active_count += 1
        
        self.total_down_label.setText(f"총 다운로드: {self.format_bytes(total_down)}/s")
        self.total_up_label.setText(f"총 업로드: {self.format_bytes(total_up)}/s")
        self.active_torrents_label.setText(f"활성 토렌트: {active_count}")
    
    def on_upload_limit_changed(self, value):
        """업로드 속도 제한 변경"""
        self.torrent_client.set_upload_limit(value)
        if value == 0:
            self.status_bar.showMessage("업로드 속도 제한 해제")
        else:
            self.status_bar.showMessage(f"업로드 속도 제한: {value} KB/s")
    
    def on_download_limit_changed(self, value):
        """다운로드 속도 제한 변경"""
        self.torrent_client.set_download_limit(value)
        if value == 0:
            self.status_bar.showMessage("다운로드 속도 제한 해제")
        else:
            self.status_bar.showMessage(f"다운로드 속도 제한: {value} KB/s")
    
    def on_auto_shutdown_toggled(self, checked):
        """자동 종료 옵션 토글"""
        self.auto_shutdown_enabled = checked
        if checked:
            self.status_bar.showMessage("자동 종료 활성화: 모든 다운로드 완료 시 컴퓨터가 종료됩니다")
        else:
            self.status_bar.showMessage("자동 종료 비활성화")
    
    def check_auto_shutdown(self):
        """자동 종료 조건 확인"""
        if not self.auto_shutdown_enabled:
            return
        
        # 토렌트가 있고 모든 토렌트가 완료되었는지 확인
        if self.torrent_client.torrents and self.torrent_client.are_all_torrents_completed():
            reply = QMessageBox.question(
                self, "자동 종료", 
                "모든 다운로드가 완료되었습니다.\n지금 컴퓨터를 종료하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.shutdown_computer()
            else:
                # 사용자가 거부하면 자동 종료 옵션 해제
                self.auto_shutdown_checkbox.setChecked(False)
                self.auto_shutdown_enabled = False
    
    def shutdown_computer(self):
        """컴퓨터 종료"""
        try:
            # macOS에서 컴퓨터 종료
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
        except subprocess.CalledProcessError:
            try:
                # 대안 명령어
                subprocess.run(["osascript", "-e", 'tell application "System Events" to shut down'], check=True)
            except:
                QMessageBox.warning(self, "종료 오류", "컴퓨터를 자동으로 종료할 수 없습니다.\n수동으로 종료해주세요.")
    
    def on_encryption_toggled(self, checked):
        """암호화 설정 토글"""
        self.torrent_client.set_encryption_enabled(checked)
        self.encryption_status_label.setText(f"암호화: {'활성화' if checked else '비활성화'}")
        self.update_security_stats()
    
    def on_dht_toggled(self, checked):
        """DHT 설정 토글"""
        self.torrent_client.set_dht_enabled(checked)
        self.dht_status_label.setText(f"DHT: {'활성화' if checked else '비활성화'}")
        self.update_security_stats()
    
    def on_block_ip_clicked(self):
        """IP 차단 버튼 클릭"""
        ip_address = self.block_ip_input.text().strip()
        if ip_address:
            try:
                # 간단한 IP 주소 형식 검증
                parts = ip_address.split('.')
                if len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts):
                    self.torrent_client.block_ip_address(ip_address)
                    self.block_ip_input.clear()
                    self.status_bar.showMessage(f"IP 주소 {ip_address}를 차단했습니다.")
                    self.update_security_stats()
                else:
                    QMessageBox.warning(self, "오류", "유효하지 않은 IP 주소 형식입니다.")
            except ValueError:
                QMessageBox.warning(self, "오류", "유효하지 않은 IP 주소 형식입니다.")
        else:
            QMessageBox.warning(self, "오류", "IP 주소를 입력해주세요.")
    
    def on_security_alert(self, event_type, message):
        """보안 알림 처리"""
        # 중요한 보안 이벤트는 팝업으로 표시
        if event_type in ["HASH_MISMATCH", "ERROR"]:
            QMessageBox.warning(self, f"보안 알림 - {event_type}", message)
        
        # 보안 로그 새로고침
        self.refresh_security_log()
        self.update_security_stats()
    
    def refresh_security_log(self):
        """보안 로그 새로고침"""
        logs = self.torrent_client.get_security_log(30)  # 최근 30개 이벤트
        self.security_log_text.clear()
        if logs:
            self.security_log_text.append('\n'.join(logs))
            # 가장 최근 로그로 스크롤
            cursor = self.security_log_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.security_log_text.setTextCursor(cursor)
    
    def clear_security_log(self):
        """보안 로그 지우기"""
        self.torrent_client.security_log.clear()
        self.security_log_text.clear()
        self.status_bar.showMessage("보안 로그를 지웠습니다.")
        self.update_security_stats()
    
    def on_anonymous_toggled(self, checked):
        """익명 모드 토글"""
        self.torrent_client.set_anonymous_mode(checked)
        self.update_security_stats()
        
    def on_proxy_type_changed(self, proxy_type):
        """프록시 타입 변경"""
        if proxy_type == "없음":
            self.proxy_host_input.setEnabled(False)
            self.proxy_port_input.setEnabled(False)
            self.proxy_apply_button.setEnabled(False)
            self.proxy_disable_button.setEnabled(False)
            # 인증 필드 숨기기
            self.proxy_username_label.hide()
            self.proxy_username_input.hide()
            self.proxy_password_label.hide()
            self.proxy_password_input.hide()
        else:
            self.proxy_host_input.setEnabled(True)
            self.proxy_port_input.setEnabled(True)
            self.proxy_apply_button.setEnabled(True)
            
            # 인증이 필요한 프록시인지 확인
            if "인증" in proxy_type:
                self.proxy_username_label.show()
                self.proxy_username_input.show()
                self.proxy_username_input.setEnabled(True)
                self.proxy_password_label.show()
                self.proxy_password_input.show()
                self.proxy_password_input.setEnabled(True)
            else:
                self.proxy_username_label.hide()
                self.proxy_username_input.hide()
                self.proxy_password_label.hide()
                self.proxy_password_input.hide()
    
    def on_proxy_apply_clicked(self):
        """프록시 설정 적용"""
        proxy_type_text = self.proxy_type_combo.currentText()
        host = self.proxy_host_input.text().strip()
        port_text = self.proxy_port_input.text().strip()
        
        if not host or not port_text:
            QMessageBox.warning(self, "오류", "프록시 주소와 포트를 입력해주세요.")
            return
        
        try:
            port = int(port_text)
        except ValueError:
            QMessageBox.warning(self, "오류", "올바른 포트 번호를 입력해주세요.")
            return
        
        # 프록시 타입 매핑
        proxy_type_map = {
            "HTTP": "http",
            "SOCKS4": "socks4", 
            "SOCKS5": "socks5",
            "HTTP (인증)": "http_pw",
            "SOCKS5 (인증)": "socks5_pw"
        }
        
        proxy_type = proxy_type_map.get(proxy_type_text)
        if not proxy_type:
            return
        
        username = self.proxy_username_input.text().strip()
        password = self.proxy_password_input.text().strip()
        
        success = self.torrent_client.set_proxy(proxy_type, host, port, username, password)
        if success:
            self.proxy_disable_button.setEnabled(True)
            QMessageBox.information(self, "성공", "프록시가 설정되었습니다.")
            self.update_security_stats()
        else:
            QMessageBox.warning(self, "오류", "프록시 설정에 실패했습니다.")
    
    def on_proxy_disable_clicked(self):
        """프록시 비활성화"""
        self.torrent_client.disable_proxy()
        self.proxy_disable_button.setEnabled(False)
        self.proxy_type_combo.setCurrentText("없음")
        self.tor_status_label.setText("Tor: 연결 안됨")
        self.update_security_stats()
    
    def on_tor_connect_clicked(self):
        """Tor 자동 연결"""
        import socket
        
        # Tor 연결 테스트
        try:
            # Tor SOCKS5 프록시 포트 테스트
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(('127.0.0.1', 9050))
            sock.close()
            
            if result == 0:
                # Tor가 실행 중이면 자동 설정
                success = self.torrent_client.set_proxy("socks5", "127.0.0.1", 9050)
                if success:
                    self.tor_status_label.setText("Tor: ✅ 연결됨")
                    self.proxy_type_combo.setCurrentText("SOCKS5")
                    self.proxy_host_input.setText("127.0.0.1")
                    self.proxy_port_input.setText("9050")
                    self.proxy_disable_button.setEnabled(True)
                    
                    # 익명 모드도 자동 활성화
                    if not self.anonymous_checkbox.isChecked():
                        self.anonymous_checkbox.setChecked(True)
                        self.torrent_client.set_anonymous_mode(True)
                    
                    QMessageBox.information(self, "성공", 
                                          "Tor에 성공적으로 연결되었습니다!\n"
                                          "• SOCKS5 프록시: 127.0.0.1:9050\n"
                                          "• 익명 모드: 활성화됨\n"
                                          "• 모든 트래픽이 Tor 네트워크를 통해 라우팅됩니다.")
                    self.update_security_stats()
                else:
                    QMessageBox.warning(self, "오류", "Tor 프록시 설정에 실패했습니다.")
            else:
                # Tor가 실행되지 않음
                reply = QMessageBox.question(self, "Tor 실행 필요", 
                                           "Tor 서비스가 실행되지 않고 있습니다.\n"
                                           "Tor를 시작하시겠습니까?",
                                           QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.start_tor_service()
                    
        except Exception as e:
            QMessageBox.warning(self, "오류", f"Tor 연결 테스트 중 오류가 발생했습니다: {e}")
    
    def start_tor_service(self):
        """Tor 서비스 시작"""
        try:
            import subprocess
            
            # Tor 서비스 시작 시도
            result = subprocess.run(['brew', 'services', 'start', 'tor'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                QMessageBox.information(self, "성공", 
                                      "Tor 서비스가 시작되었습니다.\n"
                                      "몇 초 후 다시 '🧅 Tor 자동 연결' 버튼을 클릭하세요.")
            else:
                QMessageBox.warning(self, "오류", 
                                  f"Tor 서비스 시작에 실패했습니다.\n"
                                  f"수동으로 터미널에서 실행하세요:\n"
                                  f"brew services start tor")
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "타임아웃", "Tor 서비스 시작 시간이 초과되었습니다.")
        except Exception as e:
            QMessageBox.warning(self, "오류", f"Tor 서비스 시작 중 오류: {e}")
    
    def check_tor_status(self):
        """Tor 상태 확인 (백그라운드)"""
        try:
            import socket
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', 9050))
            sock.close()
            
            # 현재 프록시가 Tor인지 확인
            anonymity_status = self.torrent_client.get_anonymity_status()
            is_using_tor = (anonymity_status['proxy_enabled'] and 
                          anonymity_status['proxy_host'] == '127.0.0.1' and 
                          anonymity_status['proxy_port'] == 9050)
            
            if result == 0:  # Tor 실행 중
                if is_using_tor:
                    self.tor_status_label.setText("Tor: ✅ 연결됨")
                else:
                    self.tor_status_label.setText("Tor: 🟡 사용 가능")
            else:  # Tor 실행 안됨
                if is_using_tor:
                    self.tor_status_label.setText("Tor: ❌ 연결 끊김")
                else:
                    self.tor_status_label.setText("Tor: 연결 안됨")
                    
        except Exception:
            # 조용히 실패 (백그라운드 체크이므로)
            pass

    def update_security_stats(self):
        """보안 통계 업데이트"""
        try:
            stats = self.torrent_client.get_security_stats()
            self.encryption_status_label.setText(f"암호화: {'활성화' if stats['encryption_enabled'] else '비활성화'}")
            self.dht_status_label.setText(f"DHT: {'활성화' if stats['dht_enabled'] else '비활성화'}")
            self.blocked_ips_count_label.setText(f"차단된 IP: {stats['blocked_ips_count']}개")
            self.security_events_count_label.setText(f"보안 이벤트: {stats['security_events_count']}개")
            
            # 익명성 상태 업데이트
            anonymity_status = self.torrent_client.get_anonymity_status()
            self.anonymity_status_label.setText(f"익명 모드: {'활성화' if anonymity_status['anonymous_mode'] else '비활성화'}")
            
            if anonymity_status['proxy_enabled']:
                self.proxy_status_label.setText(f"프록시: {anonymity_status['proxy_host']}:{anonymity_status['proxy_port']}")
            else:
                self.proxy_status_label.setText("프록시: 비활성화")
                
        except Exception as e:
            print(f"보안 통계 업데이트 오류: {e}")
    
    def closeEvent(self, event):
        """앱 종료 시 토렌트 클라이언트 정리"""
        self.update_timer.stop()
        self.tor_check_timer.stop()
        self.torrent_client.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Simple Torrent Client")
    
    # 다크 테마 스타일 적용
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QTableWidget {
            background-color: #3c3c3c;
            color: #ffffff;
            gridline-color: #555555;
            selection-background-color: #4a90e2;
        }
        QTableWidget::item {
            padding: 8px;
        }
        QPushButton {
            background-color: #4a90e2;
            color: #ffffff;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #357abd;
        }
        QPushButton:pressed {
            background-color: #2968a3;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #555555;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QProgressBar {
            border: 2px solid #555555;
            border-radius: 5px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #4a90e2;
            border-radius: 3px;
        }
        QSpinBox {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 4px;
            min-width: 80px;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #4a90e2;
            border: none;
            width: 16px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #357abd;
        }
        QCheckBox {
            color: #ffffff;
            spacing: 5px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        QCheckBox::indicator:unchecked {
            background-color: #3c3c3c;
            border: 2px solid #555555;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked {
            background-color: #4a90e2;
            border: 2px solid #4a90e2;
            border-radius: 3px;
        }
        QTabWidget::pane {
            background-color: #3c3c3c;
            border: 1px solid #555555;
        }
        QTabBar::tab {
            background-color: #2b2b2b;
            color: #ffffff;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #4a90e2;
            color: #ffffff;
        }
        QTabBar::tab:hover {
            background-color: #357abd;
        }
        QTextEdit {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 3px;
        }
        QLineEdit {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 4px;
        }
        QComboBox {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 4px;
            min-width: 100px;
        }
        QComboBox::drop-down {
            background-color: #4a90e2;
            border: none;
            width: 20px;
        }
        QComboBox::down-arrow {
            width: 12px;
            height: 12px;
        }
        QComboBox QAbstractItemView {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #555555;
            selection-background-color: #4a90e2;
        }
    """)
    
    window = TorrentMainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 
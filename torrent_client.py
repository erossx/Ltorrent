import libtorrent as lt
import time
import os
import hashlib
import random
import requests
from threading import Thread
from PySide6.QtCore import QObject, Signal


class TorrentClient(QObject):
    # 신호 정의
    progress_updated = Signal(str, float, float, float, int, int)  # hash, progress, down_rate, up_rate, seeds, peers
    torrent_added = Signal(str, str)  # hash, name
    torrent_finished = Signal(str)  # hash
    security_alert = Signal(str, str)  # type, message
    
    def __init__(self):
        super().__init__()
        self.session = lt.session()
        
        # 보안 설정
        self.blocked_ips = set()
        self.security_enabled = True
        self.encryption_enabled = True
        self.dht_enabled = True
        self.pex_enabled = True
        self.security_log = []
        
        # 랜덤 포트 사용 (보안 강화)
        random_port = random.randint(49152, 65535)
        self.session.listen_on(random_port, random_port + 10)
        
        self.torrents = {}
        self.running = True
        self.completed_torrents = set()  # 완료된 토렌트 추적
        
        # 보안 강화된 세션 설정
        settings = {
            'user_agent': 'Simple Torrent Client',
            'alert_mask': lt.alert.category_t.all_categories,
            'upload_rate_limit': 0,  # 0 = 무제한
            'download_rate_limit': 0,  # 0 = 무제한
            
            # 보안 설정
            'enable_outgoing_utp': True,
            'enable_incoming_utp': True,
            'enable_outgoing_tcp': True,
            'enable_incoming_tcp': True,
            
            # 암호화 설정
            'out_enc_policy': lt.enc_policy.enabled if self.encryption_enabled else lt.enc_policy.disabled,
            'in_enc_policy': lt.enc_policy.enabled if self.encryption_enabled else lt.enc_policy.disabled,
            'allowed_enc_level': lt.enc_level.both,
            
            # DHT 및 PEX 설정
            'enable_dht': self.dht_enabled,
            'enable_lsd': True,
            'enable_upnp': False,  # 보안상 비활성화
            'enable_natpmp': False,  # 보안상 비활성화
            
            # 기타 보안 설정
            'anonymous_mode': False,
            'force_proxy': False
        }
        self.session.apply_settings(settings)
        
        # IP 필터 로드
        self.load_ip_filter()
        
        # 상태 업데이트 스레드 시작
        self.update_thread = Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
    
    def add_torrent(self, torrent_path, download_path=None):
        """토렌트 파일 추가"""
        try:
            if download_path is None:
                download_path = os.path.expanduser("~/Downloads")
            
            # 토렌트 파일 읽기
            with open(torrent_path, 'rb') as f:
                torrent_data = f.read()
            
            # 토렌트 정보 생성
            torrent_info = lt.torrent_info(torrent_data)
            
            # 토렌트 매개변수 설정
            params = {
                'ti': torrent_info,
                'save_path': download_path,
                'storage_mode': lt.storage_mode_t.storage_mode_sparse,
            }
            
            # 토렌트 핸들 추가
            handle = self.session.add_torrent(params)
            handle.resume()
            
            # 토렌트 정보 저장
            torrent_hash = str(torrent_info.info_hash())
            self.torrents[torrent_hash] = {
                'handle': handle,
                'name': torrent_info.name(),
                'size': torrent_info.total_size(),
                'path': download_path
            }
            
            self.torrent_added.emit(torrent_hash, torrent_info.name())
            return torrent_hash
            
        except Exception as e:
            print(f"토렌트 추가 오류: {e}")
            return None
    
    def add_magnet_link(self, magnet_uri, download_path=None):
        """마그넷 링크 추가"""
        try:
            if download_path is None:
                download_path = os.path.expanduser("~/Downloads")
            
            # 마그넷 링크 파싱
            params = lt.parse_magnet_uri(magnet_uri)
            params['save_path'] = download_path
            
            # 토렌트 핸들 추가
            handle = self.session.add_torrent(params)
            handle.resume()
            
            # 임시 해시 생성 (메타데이터를 받을 때까지)
            temp_hash = str(handle.info_hash())
            self.torrents[temp_hash] = {
                'handle': handle,
                'name': '메타데이터 수신 중...',
                'size': 0,
                'path': download_path
            }
            
            self.torrent_added.emit(temp_hash, '메타데이터 수신 중...')
            return temp_hash
            
        except Exception as e:
            print(f"마그넷 링크 추가 오류: {e}")
            return None
    
    def pause_torrent(self, torrent_hash):
        """토렌트 일시정지"""
        if torrent_hash in self.torrents:
            self.torrents[torrent_hash]['handle'].pause()
    
    def resume_torrent(self, torrent_hash):
        """토렌트 재개"""
        if torrent_hash in self.torrents:
            self.torrents[torrent_hash]['handle'].resume()
    
    def remove_torrent(self, torrent_hash, delete_files=False):
        """토렌트 제거"""
        if torrent_hash in self.torrents:
            handle = self.torrents[torrent_hash]['handle']
            if delete_files:
                self.session.remove_torrent(handle, lt.options_t.delete_files)
            else:
                self.session.remove_torrent(handle)
            del self.torrents[torrent_hash]
    
    def get_torrent_status(self, torrent_hash):
        """토렌트 상태 정보 반환"""
        if torrent_hash in self.torrents:
            handle = self.torrents[torrent_hash]['handle']
            status = handle.status()
            return {
                'name': self.torrents[torrent_hash]['name'],
                'progress': status.progress,
                'download_rate': status.download_rate,
                'upload_rate': status.upload_rate,
                'num_seeds': status.num_seeds,
                'num_peers': status.num_peers,
                'state': str(status.state),
                'total_size': self.torrents[torrent_hash]['size']
            }
        return None
    
    def set_upload_limit(self, limit_kbps):
        """업로드 속도 제한 설정 (KB/s)"""
        try:
            if limit_kbps <= 0:
                # 0 또는 음수면 무제한
                self.session.set_upload_rate_limit(0)
            else:
                # KB/s를 B/s로 변환
                limit_bytes = int(limit_kbps * 1024)
                self.session.set_upload_rate_limit(limit_bytes)
        except Exception as e:
            print(f"업로드 속도 제한 설정 오류: {e}")
    
    def set_download_limit(self, limit_kbps):
        """다운로드 속도 제한 설정 (KB/s)"""
        try:
            if limit_kbps <= 0:
                # 0 또는 음수면 무제한
                self.session.set_download_rate_limit(0)
            else:
                # KB/s를 B/s로 변환
                limit_bytes = int(limit_kbps * 1024)
                self.session.set_download_rate_limit(limit_bytes)
        except Exception as e:
            print(f"다운로드 속도 제한 설정 오류: {e}")
    
    def get_session_stats(self):
        """세션 통계 반환"""
        try:
            stats = self.session.status()
            return {
                'upload_rate': stats.upload_rate,
                'download_rate': stats.download_rate,
                'total_upload': stats.total_upload,
                'total_download': stats.total_download
            }
        except:
            return {
                'upload_rate': 0,
                'download_rate': 0,
                'total_upload': 0,
                'total_download': 0
            }
    
    def _update_loop(self):
        """상태 업데이트 루프"""
        while self.running:
            try:
                # 알림 처리
                alerts = self.session.pop_alerts()
                for alert in alerts:
                    if isinstance(alert, lt.metadata_received_alert):
                        # 메타데이터 수신 완료
                        handle = alert.handle
                        torrent_hash = str(handle.info_hash())
                        if torrent_hash in self.torrents:
                            torrent_info = handle.torrent_file()
                            self.torrents[torrent_hash]['name'] = torrent_info.name()
                            self.torrents[torrent_hash]['size'] = torrent_info.total_size()
                    
                    elif isinstance(alert, lt.torrent_finished_alert):
                        # 다운로드 완료
                        torrent_hash = str(alert.handle.info_hash())
                        self.completed_torrents.add(torrent_hash)
                        self.torrent_finished.emit(torrent_hash)
                
                # 각 토렌트의 상태 업데이트
                for torrent_hash, torrent_data in self.torrents.items():
                    try:
                        status = torrent_data['handle'].status()
                        self.progress_updated.emit(
                            torrent_hash,
                            status.progress,
                            status.download_rate,
                            status.upload_rate,
                            status.num_seeds,
                            status.num_peers
                        )
                    except:
                        pass
                
                time.sleep(1)  # 1초마다 업데이트
                
            except Exception as e:
                print(f"업데이트 루프 오류: {e}")
                time.sleep(1)
    
    def are_all_torrents_completed(self):
        """모든 토렌트가 완료되었는지 확인"""
        if not self.torrents:
            return False
        
        active_torrents = set(self.torrents.keys())
        return active_torrents.issubset(self.completed_torrents)
    
    def get_active_torrent_count(self):
        """활성 토렌트 수 반환"""
        active_count = 0
        for torrent_hash in self.torrents.keys():
            if torrent_hash not in self.completed_torrents:
                status = self.get_torrent_status(torrent_hash)
                if status and (status['download_rate'] > 0 or status['progress'] < 1.0):
                    active_count += 1
        return active_count
    
    def load_ip_filter(self):
        """악성 IP 필터 로드"""
        try:
            # 기본 차단 IP 범위 (예시)
            known_bad_ranges = [
                # 예시: 악성으로 알려진 IP 범위들
                ('0.0.0.0', '0.255.255.255'),  # 예약된 주소
                ('127.0.0.0', '127.255.255.255'),  # 로컬호스트
                ('169.254.0.0', '169.254.255.255'),  # 링크 로컬
                ('224.0.0.0', '239.255.255.255'),  # 멀티캐스트
                ('240.0.0.0', '255.255.255.255'),  # 예약된 클래스 E
            ]
            
            ip_filter = lt.ip_filter()
            for start_ip, end_ip in known_bad_ranges:
                try:
                    ip_filter.add_rule(start_ip, end_ip, 1)  # 1 = 차단
                except:
                    pass
            
            self.session.set_ip_filter(ip_filter)
            self.log_security_event("IP_FILTER", f"IP 필터 로드 완료: {len(known_bad_ranges)}개 범위 차단")
        except Exception as e:
            self.log_security_event("ERROR", f"IP 필터 로드 실패: {e}")
    
    def log_security_event(self, event_type, message):
        """보안 이벤트 로그"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {event_type}: {message}"
        self.security_log.append(log_entry)
        
        # 로그가 너무 많아지면 오래된 것 삭제
        if len(self.security_log) > 1000:
            self.security_log = self.security_log[-500:]
        
        # 시그널 발생
        self.security_alert.emit(event_type, message)
        print(log_entry)  # 디버그용
    
    def verify_file_hash(self, file_path, expected_hash):
        """다운로드된 파일의 해시 검증"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            actual_hash = sha256_hash.hexdigest()
            if actual_hash == expected_hash:
                self.log_security_event("HASH_VERIFY", f"파일 해시 검증 성공: {os.path.basename(file_path)}")
                return True
            else:
                self.log_security_event("HASH_MISMATCH", f"파일 해시 불일치: {os.path.basename(file_path)}")
                return False
        except Exception as e:
            self.log_security_event("HASH_ERROR", f"해시 검증 오류: {e}")
            return False
    
    def set_encryption_enabled(self, enabled):
        """암호화 설정 변경"""
        self.encryption_enabled = enabled
        settings = self.session.get_settings()
        if enabled:
            settings['out_enc_policy'] = lt.enc_policy.enabled
            settings['in_enc_policy'] = lt.enc_policy.enabled
            self.log_security_event("ENCRYPTION", "피어 간 암호화 활성화")
        else:
            settings['out_enc_policy'] = lt.enc_policy.disabled
            settings['in_enc_policy'] = lt.enc_policy.disabled
            self.log_security_event("ENCRYPTION", "피어 간 암호화 비활성화")
        
        self.session.apply_settings(settings)
    
    def set_dht_enabled(self, enabled):
        """DHT 설정 변경"""
        self.dht_enabled = enabled
        settings = self.session.get_settings()
        settings['enable_dht'] = enabled
        self.session.apply_settings(settings)
        
        if enabled:
            self.log_security_event("DHT", "DHT 활성화")
        else:
            self.log_security_event("DHT", "DHT 비활성화 (익명성 강화)")
    
    def block_ip_address(self, ip_address):
        """특정 IP 주소 차단"""
        try:
            self.blocked_ips.add(ip_address)
            ip_filter = self.session.get_ip_filter()
            ip_filter.add_rule(ip_address, ip_address, 1)  # 1 = 차단
            self.session.set_ip_filter(ip_filter)
            self.log_security_event("IP_BLOCK", f"IP 주소 차단: {ip_address}")
        except Exception as e:
            self.log_security_event("ERROR", f"IP 차단 실패: {e}")
    
    def get_security_log(self, last_n=50):
        """보안 로그 반환"""
        return self.security_log[-last_n:] if self.security_log else []
    
    def get_security_stats(self):
        """보안 통계 반환"""
        return {
            'encryption_enabled': self.encryption_enabled,
            'dht_enabled': self.dht_enabled,
            'blocked_ips_count': len(self.blocked_ips),
            'security_events_count': len(self.security_log)
        }
    
    def stop(self):
        """클라이언트 종료"""
        self.log_security_event("SHUTDOWN", "토렌트 클라이언트 종료")
        self.running = False
        self.session.pause() 
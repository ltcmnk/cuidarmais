import json
import threading
import time
import traceback
from datetime import datetime
import paho.mqtt.client as mqtt

from app.models.storage import load_data, save_data
from app.utils import log_action


class MQTTService:
    """Lightweight MQTT service that runs the client loop in background and
    calls into the storage layer inside the Flask app context.

    Usage: mqtt = MQTTService(app); mqtt.start(); mqtt.stop()
    """

    def __init__(self, app):
        self.app = app
        cfg = app.config
        self.broker = cfg.get('MQTT_BROKER', 'broker.hivemq.com')
        self.port = cfg.get('MQTT_PORT', 1883)
        self.topic = cfg.get('MQTT_TOPIC', 'hospital/cajuru/ponto')
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self._started = False
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self._started:
                return
            try:
                self.client.connect(self.broker, self.port, keepalive=60)
                # run network loop in background thread
                self.client.loop_start()
                self._started = True
                self.app.logger.info('MQTTService started (broker=%s topic=%s)', self.broker, self.topic)
            except Exception:
                self.app.logger.exception('Failed to start MQTT client')

    def stop(self):
        with self._lock:
            if not self._started:
                return
            try:
                self.client.disconnect()
            except Exception:
                pass
            try:
                self.client.loop_stop()
            except Exception:
                pass
            self._started = False
            self.app.logger.info('MQTTService stopped')

    # Callbacks
    def on_connect(self, client, userdata, flags, rc):
        try:
            self.app.logger.info('Connected to MQTT broker rc:%s', rc)
            client.subscribe(self.topic)
        except Exception:
            self.app.logger.exception('on_connect error')

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode()
            data_msg = json.loads(payload)
            uid = data_msg.get('uid')
            if not uid:
                self.app.logger.warning('MQTT message without uid: %s', payload)
                return

            # use app context to safely access storage (or DB later)
            with self.app.app_context():
                data = load_data()
                user = next((u for u in data.get('users', []) if u.get('codigo_cracha') == uid), None)
                if not user:
                    self.app.logger.warning('UID %s not registered to any user', uid)
                    return

                user_id = user['id']
                user_name = user.get('nome_completo') or user.get('nome')

                entries = [e for e in data.get('clock_entries', []) if e.get('userId') == user_id]
                last_type = entries[-1].get('type') if entries else None
                next_type = 'out' if last_type == 'in' else 'in'

                new_entry = {
                    'id': str(len(data.get('clock_entries', [])) + 1),
                    'userId': user_id,
                    'type': next_type,
                    'timestamp': datetime.now().isoformat(),
                    'notes': 'Registro automático via RFID'
                }

                data.setdefault('clock_entries', []).append(new_entry)
                save_data(data)
                try:
                    log_action(user_id, 'rfid_clock', {'uid': uid, 'type': next_type})
                except Exception:
                    pass
                self.app.logger.info('RFID clock (%s) created for %s (%s)', next_type, user_name, uid)

        except Exception:
            self.app.logger.error('Error processing MQTT message: %s', traceback.format_exc())

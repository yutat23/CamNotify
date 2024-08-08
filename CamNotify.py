import cv2
import threading
import time
import tkinter as tk
from tkinter import messagebox
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import configparser

class SlackImagePoster:
    def __init__(self, root):
        self.root = root
        self.root.title("Slack Image Poster")

        # Load configuration
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        self.slack_token = self.config.get('Slack', 'token', fallback='')
        self.slack_channel = self.config.get('Slack', 'channel', fallback='')
        self.interval = self.config.getint('Settings', 'interval', fallback=60)
        self.camera_index = self.config.getint('Settings', 'camera_index', fallback=0)

        self.running = False
        self.thread = None

        self.setup_ui()

    def setup_ui(self):
        tk.Label(self.root, text="Slack API Token:").grid(row=0, column=0, padx=5, pady=5)
        self.token_entry = tk.Entry(self.root, width=50)
        self.token_entry.grid(row=0, column=1, padx=5, pady=5)
        self.token_entry.insert(0, self.slack_token)

        tk.Label(self.root, text="Slack Channel ID:").grid(row=1, column=0, padx=5, pady=5)
        self.channel_entry = tk.Entry(self.root, width=50)
        self.channel_entry.grid(row=1, column=1, padx=5, pady=5)
        self.channel_entry.insert(0, self.slack_channel)

        tk.Label(self.root, text="Interval (seconds):").grid(row=2, column=0, padx=5, pady=5)
        self.interval_entry = tk.Entry(self.root, width=50)
        self.interval_entry.grid(row=2, column=1, padx=5, pady=5)
        self.interval_entry.insert(0, str(self.interval))

        tk.Label(self.root, text="Camera Index:").grid(row=3, column=0, padx=5, pady=5)
        self.camera_index_var = tk.IntVar(value=self.camera_index)
        self.camera_menu = tk.OptionMenu(self.root, self.camera_index_var, *self.get_available_cameras())
        self.camera_menu.grid(row=3, column=1, padx=5, pady=5)

        self.start_button = tk.Button(self.root, text="START", command=self.start)
        self.start_button.grid(row=4, column=0, padx=5, pady=5)

        self.stop_button = tk.Button(self.root, text="STOP", command=self.stop)
        self.stop_button.grid(row=4, column=1, padx=5, pady=5)

    def get_available_cameras(self):
        index = 0
        arr = []
        while True:
            cap = cv2.VideoCapture(index)
            if not cap.read()[0]:
                break
            else:
                arr.append(index)
            cap.release()
            index += 1
        return arr

    def save_config(self):
        self.config['Slack'] = {
            'token': self.token_entry.get(),
            'channel': self.channel_entry.get()
        }
        self.config['Settings'] = {
            'interval': self.interval_entry.get(),
            'camera_index': self.camera_index_var.get()
        }
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)

    def capture_image(self):
        cap = cv2.VideoCapture(self.camera_index_var.get())
        if not cap.isOpened():
            raise Exception("カメラを開くことができませんでした")
        ret, frame = cap.read()
        if not ret:
            raise Exception("画像をキャプチャできませんでした")
        cap.release()
        image_path = 'captured_image.jpg'
        cv2.imwrite(image_path, frame)
        return image_path

    def post_image_to_slack(self, image_path):
        client = WebClient(token=self.slack_token)
        try:
            response = client.files_upload_v2(
                channel=self.slack_channel,
                file=image_path,
                title="Captured Image"
            )
            assert response["file"]
            print("画像をSlackに投稿しました")
        except SlackApiError as e:
            print(f"エラーが発生しました: {e.response['error']}")

    def periodic_post(self):
        while self.running:
            image_path = self.capture_image()
            self.post_image_to_slack(image_path)
            time.sleep(self.interval)

    def start(self):
        self.save_config()
        self.slack_token = self.token_entry.get()
        self.slack_channel = self.channel_entry.get()
        self.interval = int(self.interval_entry.get())
        self.camera_index = self.camera_index_var.get()
        self.running = True
        self.thread = threading.Thread(target=self.periodic_post)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
            self.thread = None

if __name__ == "__main__":
    root = tk.Tk()
    app = SlackImagePoster(root)
    root.mainloop()

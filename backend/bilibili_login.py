"""
B站扫码登录工具 — 只需扫一次，自动保存凭证
"""
import json
import time
import os
import shutil
from pathlib import Path
from bilibili_api import login_v2, sync

CRED_FILE = Path(__file__).resolve().parent / 'bilearn_credential.json'
QR_FILE = Path(__file__).resolve().parent / 'bilearn_qrcode.png'


def login():
    qr = login_v2.QrCodeLogin()
    sync(qr.generate_qrcode())

    pic = qr.get_qrcode_picture()
    if pic and pic.url:
        src = pic.url.replace('file://', '')
        shutil.copy2(src, str(QR_FILE))
        os.startfile(str(QR_FILE))
        print(f'二维码已保存并打开: {QR_FILE}')

    print('\n请用 B站手机APP 扫描二维码登录...')
    while True:
        time.sleep(1)
        sync(qr.check_state())
        print('.', end='', flush=True)
        if qr.has_done():
            print(' scanned!')
            break

    cred = qr.get_credential()

    data = {
        'sessdata': cred.sessdata,
        'bili_jct': cred.bili_jct,
        'buvid3': cred.buvid3,
        'dedeuserid': cred.dedeuserid,
    }
    CRED_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'\n登录成功！用户ID: {data["dedeuserid"]}')
    print(f'凭证已保存到 {CRED_FILE}')
    print('现在启动服务器即可自动获取B站字幕！')
    return data


if __name__ == '__main__':
    try:
        login()
        input('\n按 Enter 退出...')
    except KeyboardInterrupt:
        print('\n已取消')
    except Exception as e:
        print(f'\n登录失败: {e}')
        import traceback
        traceback.print_exc()
        input('\n按 Enter 退出...')

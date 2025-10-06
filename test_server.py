#!/usr/bin/env python3
"""
簡易テストサーバー
"""

import os
import sys
from app import create_app

def main():
    try:
        print("システム初期化中...")
        app, socketio = create_app('development')
        print("システム初期化完了")
        
        print("サーバー起動中...")
        socketio.run(
            app, 
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
        
    except Exception as e:
        print(f"エラー: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
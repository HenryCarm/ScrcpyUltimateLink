[app]
title = Scrcpy Heartbeat
package.name = scrcpyheartbeat
package.domain = org.henry.scrcpy
source.dir = android
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3,kivy,requests
orientation = portrait
osx.python_version = 3
osx.kivy_version = 1.11.1
android.archs = arm64-v8a
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b

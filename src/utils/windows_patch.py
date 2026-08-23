# src/utils/windows_patch.py
"""
Windows Compatibility Patch
Fixes the 'No module named pwd' error on Windows
"""
import sys
import importlib

if sys.platform == 'win32':
    # Create a mock pwd module
    class MockPwd:
        def getpwuid(self, uid):
            class MockUser:
                pw_name = 'windows_user'
                pw_uid = uid
                pw_gid = 1000
                pw_dir = 'C:\\Users\\user'
                pw_shell = 'cmd.exe'
                pw_gecos = 'Windows User'
                pw_passwd = 'x'
            return MockUser()
        
        def getpwnam(self, name):
            return self.getpwuid(1000)
        
        def getpwall(self):
            return []
    
    # Register the mock module
    sys.modules['pwd'] = MockPwd()
    print("✅ Windows pwd module patched successfully")
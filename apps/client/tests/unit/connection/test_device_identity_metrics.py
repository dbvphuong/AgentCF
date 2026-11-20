import sys
import pytest
from agent_cf_client.desktop import identity, metrics


@pytest.mark.skipif(sys.platform!='win32',reason='Windows DPAPI')
def test_identity_persists_and_proof_is_encrypted(tmp_path,monkeypatch):
    monkeypatch.setattr(identity,'machine_identity',lambda:'device-'+'a'*64)
    first=identity.device_identity(tmp_path)
    assert first==identity.device_identity(tmp_path)
    assert len(first['device_key'])==64
    assert first['device_key'].encode() not in (tmp_path/'device-identity.dpapi').read_bytes()
    other=identity.device_identity(tmp_path/'other-profile')
    assert other['device_id']==first['device_id']
    assert other['device_key']!=first['device_key']


def test_metrics_reports_real_deltas_and_memory_from_os_api(monkeypatch):
    class Kernel:
        call=0
        def GlobalMemoryStatusEx(self,ptr):
            ptr._obj.total=16*1024**3;ptr._obj.available=6*1024**3
            return 1
        def GetSystemTimes(self,idle,kernel,user):
            self.call+=1
            idle._obj.dwLowDateTime=10 if self.call==1 else 30
            kernel._obj.dwLowDateTime=100*self.call
            user._obj.dwLowDateTime=100*self.call
            return 1
    fake=Kernel()
    monkeypatch.setattr(metrics.sys,'platform','win32')
    monkeypatch.setattr(metrics.ctypes,'WinDLL',lambda *a,**k:fake,raising=False)
    sampler=metrics.SystemMetrics()
    assert 'cpu_percent' not in sampler.sample()
    measured=sampler.sample()
    assert measured['cpu_percent']==90
    assert measured['ram_percent']==62.5
    assert measured['memory_used_bytes']==10*1024**3
    assert measured['memory_total_bytes']==16*1024**3

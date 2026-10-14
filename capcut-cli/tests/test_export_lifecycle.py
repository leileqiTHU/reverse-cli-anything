"""Failure-path cleanup of the scoped post-export side-effect guard."""
from pathlib import Path
from types import SimpleNamespace
import sys,time,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from capcut_export import render_frontend

class ExportLifecycle(unittest.TestCase):
    def exercise(self,fail):
        calls=[];front=SimpleNamespace();observer=SimpleNamespace()
        def log(name,value=None):
            def call(*args):calls.append(name);return value
            return call
        def install(*args):
            calls.append('guard-install')
            if fail=='install':raise ValueError('ABI guard rejected')
            return {'installed':True}
        def configure(*args):raise ValueError('configuration rejected')
        front.exports_sync=SimpleNamespace(exportopen=log('open',{}),exportguardinstall=install,
            exportguardremove=log('guard-remove',{}),exportinspect=log('inspect',{'models':[{'className':name} for name in ['ExportWindowViewModel','ExportHomeBottomViewModel','ExportFileSelectorPanelViewModel','ExportVideoOptionsPanelViewModel']]}),
            exportstatus=log('status',{'stage':'HOME','preparing':'false','isTryExporting':'false'}),exportconfigure=configure,
            exportclose=log('close',{'closeAccepted':True}))
        for item in (front,observer):item.on=lambda *args:None;item.load=lambda:None;item.unload=log('unload')
        queue=iter([front,observer]);session=SimpleNamespace(create_script=lambda _:next(queue))
        with self.assertRaisesRegex(ValueError,'ABI guard rejected' if fail=='install' else 'configuration rejected'):
            render_frontend({'deadline_monotonic':time.monotonic()+100},session)
        return calls
    def test_guard_removed_after_owned_window_closed_on_configuration_failure(self):
        calls=self.exercise('configure');self.assertLess(calls.index('close'),calls.index('guard-remove'))
    def test_rejected_abi_closes_window_without_assuming_hook_installed(self):
        calls=self.exercise('install');self.assertIn('close',calls);self.assertNotIn('guard-remove',calls)

if __name__=='__main__':unittest.main()

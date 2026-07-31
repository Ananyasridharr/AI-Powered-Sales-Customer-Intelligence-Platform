import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logging
from datetime import datetime
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
class ValidationResult:
    def __init__(self, rule_id, rule_name, passed, failed_count, total_count, sample_failures=None):
        self.rule_id=rule_id; self.rule_name=rule_name; self.passed=passed
        self.failed_count=failed_count; self.total_count=total_count
        self.pass_rate=round((total_count-failed_count)/total_count*100,2) if total_count else 0
        self.sample_failures=sample_failures or []
class BaseValidator:
    def __init__(self, df, table_name, engine=None):
        self.df=df.copy(); self.table_name=table_name; self.engine=engine
        self.results=[]; self.log=logging.getLogger(self.__class__.__name__)
        self.log.info(f"Initialising validator for '{table_name}' — {len(df):,} rows")
    def _check(self, rule_id, rule_name, mask, threshold_pct=100.0):
        total=len(self.df); failed_count=int((~mask).sum())
        pass_rate=(total-failed_count)/total*100 if total else 0
        passed=pass_rate>=threshold_pct
        sample=self.df[~mask].head(5).to_dict(orient='records') if failed_count>0 else []
        result=ValidationResult(rule_id,rule_name,passed,failed_count,total,sample)
        self.results.append(result)
        status='PASS' if passed else 'FAIL'
        msg=f'[{status}] {rule_id} — {rule_name} | {failed_count:,} failures / {total:,} rows ({pass_rate:.2f}% clean)'
        self.log.info(msg) if passed else self.log.warning(msg)
        return result
    def validate(self):
        raise NotImplementedError
    def summary(self):
        total=len(self.results); passed=sum(1 for r in self.results if r.passed); failed=total-passed
        print('\n'+'='*65)
        print(f'  VALIDATION REPORT — {self.table_name.upper()}')
        print(f'  Run at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        print('='*65)
        for r in self.results:
            s='OK' if r.passed else 'XX'
            print(f'  [{s}] {r.rule_id} — {r.rule_name}')
            print(f'       Failures: {r.failed_count:,} / {r.total_count:,}  |  {r.pass_rate}% clean')
        print('-'*65)
        marker='ALL CLEAR' if failed==0 else ('WARNINGS' if failed<=2 else 'CRITICAL')
        print(f'  Result: {passed}/{total} rules passed  [{marker}]')
        print('='*65+'\n')
        return {'passed':passed,'failed':failed,'total':total,'results':self.results}

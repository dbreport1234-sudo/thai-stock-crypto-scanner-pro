import unittest
import pandas as pd
import numpy as np
from scanner.indicators import add_indicators

class IndicatorTests(unittest.TestCase):
    def test_indicator_columns_exist(self):
        n=120
        close=pd.Series(np.linspace(10,20,n)+np.sin(np.arange(n)))
        df=pd.DataFrame({"open":close,"high":close+0.5,"low":close-0.5,"close":close,"volume":1000})
        out=add_indicators(df)
        for col in ["ema20","ema50","rsi","macd_hist","atr","prior_high20","vol_avg20"]:
            self.assertIn(col,out.columns)
        self.assertTrue(out["ema20"].notna().all())
if __name__=="__main__": unittest.main()

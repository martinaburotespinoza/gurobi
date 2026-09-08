from gurobean.model import Scenario, expected_newsvendor_profit, solve_round1_closed_form, solve_round1_scipy

def test_round1_hits_resource_cap():
 s=Scenario(lambda_total=25,p_hot=1,revenue_hot=1,beans_available=25,beans_hot=1,water_available=100,water_hot=1); assert solve_round1_closed_form(s)['Q_hot']==25

def test_profit_increases_in_r1():
 s=Scenario(lambda_total=25,p_hot=1,revenue_hot=1); assert expected_newsvendor_profit(25,25,1,0)>expected_newsvendor_profit(20,25,1,0)

def test_closed_and_scipy_are_close():
 s=Scenario(lambda_total=25,p_hot=1,revenue_hot=1,beans_available=25,beans_hot=1,water_available=100,water_hot=1); a=solve_round1_closed_form(s); b=solve_round1_scipy(s); assert abs(a['Q_hot']-b['Q_hot'])<1e-3

def test_r1_salvage_only_demand_zero_uses_cap():
 s=Scenario(lambda_total=0,revenue_hot=0,salvage_hot=0.25,beans_available=10,beans_hot=1,water_available=10,water_hot=1)
 assert solve_round1_closed_form(s)['Q_hot']==10

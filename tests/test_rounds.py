from gurobean.model import RoundConfig
def test_round_progression():
 r=[RoundConfig.for_round(i) for i in range(1,9)]
 assert not r[0].include_cold and not r[0].include_brew_cost
 assert r[1].include_cold and not r[1].include_brew_cost
 assert r[2].include_brew_cost and not r[2].include_markup
 assert r[4].include_markup and r[5].include_balking and r[6].include_multi_cup and r[7].include_service_rate

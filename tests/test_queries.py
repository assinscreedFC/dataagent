"""Tests des queries business sur le mini Olist."""

from dataagent.data import queries


def test_revenue_by_month_excludes_non_delivered(conn):
    df = queries.revenue_by_month(conn)
    rows = {r["month"]: r["revenue"] for r in df.to_dicts()}
    # o4 (canceled) exclu ; o1+o2 en janvier, o3 en février
    assert rows == {"2017-01": 300.0, "2017-02": 50.0}


def test_top_categories_ordered_by_revenue(conn):
    df = queries.top_categories(conn)
    rows = df.to_dicts()
    # moveis : o2(200)+o4(30)=230 ; informatica : o1(100)+o3(50)=150
    assert rows[0] == {"category": "moveis", "revenue": 230.0}
    assert rows[1] == {"category": "informatica", "revenue": 150.0}


def test_top_categories_respects_limit(conn):
    df = queries.top_categories(conn, n=1)
    assert df.height == 1
    assert df.to_dicts()[0]["category"] == "moveis"


def test_delivery_delay_vs_review(conn):
    df = queries.delivery_delay_vs_review(conn)
    rows = {r["review_score"]: r["avg_delivery_days"] for r in df.to_dicts()}
    # o1: 5j (score5), o2: 3j (score4), o3: 10j (score2)
    assert rows == {2: 10.0, 4: 3.0, 5: 5.0}


def test_orders_by_status(conn):
    df = queries.orders_by_status(conn)
    rows = {r["status"]: r["n"] for r in df.to_dicts()}
    assert rows == {"delivered": 3, "canceled": 1}


def test_avg_review_score_by_month(conn):
    df = queries.avg_review_score_by_month(conn)
    rows = {r["month"]: r["avg_score"] for r in df.to_dicts()}
    # janvier : (5+4)/2=4.5 ; février : 2.0
    assert rows == {"2017-01": 4.5, "2017-02": 2.0}

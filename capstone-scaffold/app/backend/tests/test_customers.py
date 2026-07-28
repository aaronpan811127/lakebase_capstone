from backend.routers.customers import (
    build_categories_sql,
    build_list_query,
    build_metrics_sql,
)


def test_list_query_no_filters():
    data_sql, data_params, count_sql, count_params = build_list_query(
        None, None, None, page=1, page_size=25
    )
    assert "WHERE" not in data_sql
    assert data_params == [25, 0]  # limit, offset
    assert count_params == []
    assert "ORDER BY lifetime_value DESC" in data_sql


def test_list_query_all_filters_and_offset():
    data_sql, data_params, count_sql, count_params = build_list_query(
        "S1", 1000.0, 0.5, page=3, page_size=10
    )
    assert data_sql.count("%s") == 5  # 3 filters + limit + offset
    assert data_params == ["S1", 1000.0, 0.5, 10, 20]
    assert count_params == ["S1", 1000.0, 0.5]
    assert "segment_id = %s" in data_sql
    assert "lifetime_value >= %s" in data_sql
    assert "churn_score <= %s" in data_sql


def test_metrics_sql_uses_gold_and_named_param():
    sql = build_metrics_sql("cat.gold")
    assert "cat.gold.transactions" in sql
    assert "cat.gold.support_tickets" in sql
    assert ":cid" in sql
    assert "status = 'completed'" in sql


def test_categories_sql_limits_5():
    sql = build_categories_sql("cat.gold")
    assert "LIMIT 5" in sql
    assert "GROUP BY p.category" in sql

from wenjia_agent.core.city_data import get_cities, get_city_coordinates, get_provinces


def test_city_lookup():
    assert "北京市" in get_provinces()
    assert "北京市" in get_cities("北京市")
    longitude, latitude = get_city_coordinates("北京市", "北京市")
    assert longitude > 100
    assert latitude > 30

def test_service(mock_service):
    assert mock_service.service_name == 'foo'
    assert next(mock_service.identifier) == 'foo0'

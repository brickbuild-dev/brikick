.PHONY: test test-unit test-integration test-cov test-file test-match

# Run all tests
test:
	pytest tests/ -v

# Run only unit tests
test-unit:
	pytest tests/unit/ -v

# Run only integration tests
test-integration:
	pytest tests/integration/ -v

# Run with coverage
test-cov:
	pytest tests/ --cov=api --cov=services --cov=db --cov-report=html --cov-report=term-missing

# Run specific test file
test-file:
	pytest $(FILE) -v

# Run tests matching pattern
test-match:
	pytest tests/ -v -k "$(PATTERN)"

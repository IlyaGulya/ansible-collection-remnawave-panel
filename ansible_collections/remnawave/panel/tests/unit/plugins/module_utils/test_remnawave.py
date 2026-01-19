# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ilya Gulya
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""Unit tests for Remnawave Ansible module utilities."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.remnawave.panel.plugins.module_utils.remnawave import (
    READ_ONLY_FIELDS,
    RemnawaveClient,
    _lists_equal,
    camel_to_snake_dict,
    recursive_diff,
    resolve_config_profile_uuid,
    resolve_inbound_uuids,
    snake_to_camel_dict,
    to_camel_case,
    to_snake_case,
)


# =============================================================================
# Tests for to_snake_case()
# =============================================================================


class TestToSnakeCase:
    """Test cases for to_snake_case() function."""

    def test_simple_camel_case(self):
        """Convert simple camelCase to snake_case."""
        assert to_snake_case("camelCase") == "camel_case"

    def test_pascal_case(self):
        """Convert PascalCase to snake_case."""
        assert to_snake_case("PascalCase") == "pascal_case"

    def test_multiple_words(self):
        """Convert camelCase with multiple words."""
        assert to_snake_case("thisIsALongName") == "this_is_a_long_name"

    def test_already_snake_case(self):
        """Already snake_case should remain unchanged."""
        assert to_snake_case("already_snake") == "already_snake"

    def test_single_word_lowercase(self):
        """Single lowercase word should remain unchanged."""
        assert to_snake_case("word") == "word"

    def test_single_word_capitalized(self):
        """Single capitalized word converts to lowercase."""
        assert to_snake_case("Word") == "word"

    def test_acronym_at_start(self):
        """Acronym at start of string."""
        assert to_snake_case("HTTPResponse") == "http_response"

    def test_acronym_in_middle(self):
        """Acronym in middle of string."""
        assert to_snake_case("getHTTPResponse") == "get_http_response"

    def test_acronym_at_end(self):
        """Acronym at end of string."""
        assert to_snake_case("responseHTTP") == "response_http"

    def test_consecutive_capitals(self):
        """Handle consecutive capital letters."""
        assert to_snake_case("XMLParser") == "xml_parser"

    def test_numbers_preserved(self):
        """Numbers should be preserved in conversion."""
        assert to_snake_case("config2Profile") == "config2_profile"

    def test_numbers_at_end(self):
        """Numbers at end should be preserved."""
        assert to_snake_case("version2") == "version2"

    def test_uuid_field(self):
        """UUID field conversion."""
        assert to_snake_case("uuid") == "uuid"

    def test_created_at_field(self):
        """createdAt field conversion."""
        assert to_snake_case("createdAt") == "created_at"

    def test_is_connected_field(self):
        """isConnected field conversion."""
        assert to_snake_case("isConnected") == "is_connected"

    def test_empty_string(self):
        """Empty string should return empty string."""
        assert to_snake_case("") == ""

    def test_api_url(self):
        """API URL style string."""
        assert to_snake_case("apiURL") == "api_url"

    def test_mixed_case_with_numbers(self):
        """Mixed case with numbers in the middle."""
        assert to_snake_case("test123Value") == "test123_value"


# =============================================================================
# Tests for to_camel_case()
# =============================================================================


class TestToCamelCase:
    """Test cases for to_camel_case() function."""

    def test_simple_snake_case(self):
        """Convert simple snake_case to camelCase."""
        assert to_camel_case("snake_case") == "snakeCase"

    def test_multiple_underscores(self):
        """Convert snake_case with multiple underscores."""
        assert to_camel_case("this_is_a_long_name") == "thisIsALongName"

    def test_already_camel_case(self):
        """Single word without underscores stays the same."""
        assert to_camel_case("camelCase") == "camelCase"

    def test_single_word(self):
        """Single word should remain unchanged."""
        assert to_camel_case("word") == "word"

    def test_two_words(self):
        """Two words separated by underscore."""
        assert to_camel_case("first_second") == "firstSecond"

    def test_numbers_preserved(self):
        """Numbers should be preserved."""
        assert to_camel_case("config_2_profile") == "config2Profile"

    def test_empty_string(self):
        """Empty string should return empty string."""
        assert to_camel_case("") == ""

    def test_created_at(self):
        """created_at converts to createdAt."""
        assert to_camel_case("created_at") == "createdAt"

    def test_is_connected(self):
        """is_connected converts to isConnected."""
        assert to_camel_case("is_connected") == "isConnected"

    def test_api_url(self):
        """api_url converts to apiUrl."""
        assert to_camel_case("api_url") == "apiUrl"

    def test_trailing_underscore(self):
        """Handle trailing underscore."""
        assert to_camel_case("trailing_") == "trailing"

    def test_leading_underscore(self):
        """Handle leading underscore - first component is empty."""
        assert to_camel_case("_leading") == "Leading"


# =============================================================================
# Tests for camel_to_snake_dict()
# =============================================================================


class TestCamelToSnakeDict:
    """Test cases for camel_to_snake_dict() function."""

    def test_simple_dict(self):
        """Convert simple dict with camelCase keys."""
        input_dict = {"firstName": "John", "lastName": "Doe"}
        expected = {"first_name": "John", "last_name": "Doe"}
        assert camel_to_snake_dict(input_dict) == expected

    def test_nested_dict(self):
        """Convert nested dict with camelCase keys."""
        input_dict = {
            "userName": "john",
            "userDetails": {"firstName": "John", "lastName": "Doe"},
        }
        expected = {
            "user_name": "john",
            "user_details": {"first_name": "John", "last_name": "Doe"},
        }
        assert camel_to_snake_dict(input_dict) == expected

    def test_list_of_dicts(self):
        """Convert list of dicts with camelCase keys."""
        input_data = [{"firstName": "John"}, {"firstName": "Jane"}]
        expected = [{"first_name": "John"}, {"first_name": "Jane"}]
        assert camel_to_snake_dict(input_data) == expected

    def test_dict_with_list_values(self):
        """Convert dict containing lists of dicts."""
        input_dict = {"userList": [{"userId": 1}, {"userId": 2}]}
        expected = {"user_list": [{"user_id": 1}, {"user_id": 2}]}
        assert camel_to_snake_dict(input_dict) == expected

    def test_deeply_nested(self):
        """Convert deeply nested structure."""
        input_dict = {
            "level1": {"level2": {"level3": {"deepValue": "test"}}}
        }
        expected = {
            "level1": {"level2": {"level3": {"deep_value": "test"}}}
        }
        assert camel_to_snake_dict(input_dict) == expected

    def test_empty_dict(self):
        """Empty dict should return empty dict."""
        assert camel_to_snake_dict({}) == {}

    def test_empty_list(self):
        """Empty list should return empty list."""
        assert camel_to_snake_dict([]) == []

    def test_primitive_values(self):
        """Primitive values should pass through unchanged."""
        assert camel_to_snake_dict("string") == "string"
        assert camel_to_snake_dict(123) == 123
        assert camel_to_snake_dict(True) is True
        assert camel_to_snake_dict(None) is None

    def test_mixed_list(self):
        """List with mixed types."""
        input_data = [{"camelKey": 1}, "string", 123, None]
        expected = [{"camel_key": 1}, "string", 123, None]
        assert camel_to_snake_dict(input_data) == expected


# =============================================================================
# Tests for snake_to_camel_dict()
# =============================================================================


class TestSnakeToCamelDict:
    """Test cases for snake_to_camel_dict() function."""

    def test_simple_dict(self):
        """Convert simple dict with snake_case keys."""
        input_dict = {"first_name": "John", "last_name": "Doe"}
        expected = {"firstName": "John", "lastName": "Doe"}
        assert snake_to_camel_dict(input_dict) == expected

    def test_nested_dict(self):
        """Convert nested dict with snake_case keys."""
        input_dict = {
            "user_name": "john",
            "user_details": {"first_name": "John", "last_name": "Doe"},
        }
        expected = {
            "userName": "john",
            "userDetails": {"firstName": "John", "lastName": "Doe"},
        }
        assert snake_to_camel_dict(input_dict) == expected

    def test_list_of_dicts(self):
        """Convert list of dicts with snake_case keys."""
        input_data = [{"first_name": "John"}, {"first_name": "Jane"}]
        expected = [{"firstName": "John"}, {"firstName": "Jane"}]
        assert snake_to_camel_dict(input_data) == expected

    def test_dict_with_list_values(self):
        """Convert dict containing lists of dicts."""
        input_dict = {"user_list": [{"user_id": 1}, {"user_id": 2}]}
        expected = {"userList": [{"userId": 1}, {"userId": 2}]}
        assert snake_to_camel_dict(input_dict) == expected

    def test_roundtrip_conversion(self):
        """Converting snake->camel->snake should return original."""
        original = {"user_name": "john", "is_active": True}
        camel = snake_to_camel_dict(original)
        back_to_snake = camel_to_snake_dict(camel)
        assert back_to_snake == original

    def test_roundtrip_conversion_camel_first(self):
        """Converting camel->snake->camel should return original."""
        original = {"userName": "john", "isActive": True}
        snake = camel_to_snake_dict(original)
        back_to_camel = snake_to_camel_dict(snake)
        assert back_to_camel == original

    def test_empty_dict(self):
        """Empty dict should return empty dict."""
        assert snake_to_camel_dict({}) == {}

    def test_primitive_values(self):
        """Primitive values should pass through unchanged."""
        assert snake_to_camel_dict("string") == "string"
        assert snake_to_camel_dict(123) == 123


# =============================================================================
# Tests for _lists_equal()
# =============================================================================


class TestListsEqual:
    """Test cases for _lists_equal() function."""

    def test_same_lists(self):
        """Identical lists should be equal."""
        assert _lists_equal([1, 2, 3], [1, 2, 3]) is True

    def test_same_elements_different_order(self):
        """Same elements in different order should be equal for simple types."""
        assert _lists_equal([1, 2, 3], [3, 2, 1]) is True

    def test_different_lengths(self):
        """Lists with different lengths should not be equal."""
        assert _lists_equal([1, 2], [1, 2, 3]) is False

    def test_empty_lists(self):
        """Empty lists should be equal."""
        assert _lists_equal([], []) is True

    def test_string_lists_same_order(self):
        """String lists with same order."""
        assert _lists_equal(["a", "b", "c"], ["a", "b", "c"]) is True

    def test_string_lists_different_order(self):
        """String lists with different order should be equal."""
        assert _lists_equal(["a", "b", "c"], ["c", "a", "b"]) is True

    def test_dict_lists_same_order(self):
        """Dict lists with same order should be equal."""
        list1 = [{"a": 1}, {"b": 2}]
        list2 = [{"a": 1}, {"b": 2}]
        assert _lists_equal(list1, list2) is True

    def test_dict_lists_different_order(self):
        """Dict lists with different order should NOT be equal (order matters for dicts)."""
        list1 = [{"a": 1}, {"b": 2}]
        list2 = [{"b": 2}, {"a": 1}]
        assert _lists_equal(list1, list2) is False

    def test_dict_lists_different_content(self):
        """Dict lists with different content should not be equal."""
        list1 = [{"a": 1}]
        list2 = [{"a": 2}]
        assert _lists_equal(list1, list2) is False

    def test_mixed_types_unhashable(self):
        """Lists with unhashable mixed types fall back to direct comparison."""
        list1 = [[1, 2], [3, 4]]
        list2 = [[1, 2], [3, 4]]
        assert _lists_equal(list1, list2) is True

    def test_mixed_types_unhashable_different_order(self):
        """Unhashable types with different order use direct comparison."""
        list1 = [[1, 2], [3, 4]]
        list2 = [[3, 4], [1, 2]]
        assert _lists_equal(list1, list2) is False


# =============================================================================
# Tests for recursive_diff()
# =============================================================================


class TestRecursiveDiff:
    """Test cases for recursive_diff() function."""

    def test_no_changes(self):
        """No changes should return None."""
        desired = {"name": "test", "value": 123}
        current = {"name": "test", "value": 123}
        assert recursive_diff(desired, current) is None

    def test_simple_value_change(self):
        """Simple value change should be detected."""
        desired = {"name": "new_name"}
        current = {"name": "old_name"}
        diff = recursive_diff(desired, current)
        assert diff == {"name": {"desired": "new_name", "current": "old_name"}}

    def test_multiple_changes(self):
        """Multiple changes should all be detected."""
        desired = {"name": "new", "value": 200}
        current = {"name": "old", "value": 100}
        diff = recursive_diff(desired, current)
        assert diff == {
            "name": {"desired": "new", "current": "old"},
            "value": {"desired": 200, "current": 100},
        }

    def test_read_only_fields_ignored(self):
        """Read-only fields should be ignored."""
        desired = {"name": "test", "uuid": "new-uuid", "createdAt": "2024-01-01"}
        current = {"name": "test", "uuid": "old-uuid", "createdAt": "2023-01-01"}
        assert recursive_diff(desired, current) is None

    def test_all_read_only_fields_ignored(self):
        """All read-only fields from READ_ONLY_FIELDS should be ignored."""
        desired = {field: "new_value" for field in READ_ONLY_FIELDS}
        desired["name"] = "test"
        current = {field: "old_value" for field in READ_ONLY_FIELDS}
        current["name"] = "test"
        assert recursive_diff(desired, current) is None

    def test_nested_dict_change(self):
        """Changes in nested dicts should be detected."""
        desired = {"config": {"setting": "new"}}
        current = {"config": {"setting": "old"}}
        diff = recursive_diff(desired, current)
        assert diff == {"config": {"setting": {"desired": "new", "current": "old"}}}

    def test_nested_dict_no_change(self):
        """Nested dicts with no change should return None."""
        desired = {"config": {"setting": "same"}}
        current = {"config": {"setting": "same"}}
        assert recursive_diff(desired, current) is None

    def test_deeply_nested_change(self):
        """Deeply nested changes should be detected."""
        desired = {"a": {"b": {"c": "new"}}}
        current = {"a": {"b": {"c": "old"}}}
        diff = recursive_diff(desired, current)
        assert diff == {"a": {"b": {"c": {"desired": "new", "current": "old"}}}}

    def test_list_change(self):
        """List changes should be detected."""
        desired = {"tags": ["a", "b"]}
        current = {"tags": ["a", "c"]}
        diff = recursive_diff(desired, current)
        assert diff == {"tags": {"desired": ["a", "b"], "current": ["a", "c"]}}

    def test_list_no_change_same_order(self):
        """Identical lists should not report changes."""
        desired = {"tags": ["a", "b"]}
        current = {"tags": ["a", "b"]}
        assert recursive_diff(desired, current) is None

    def test_list_no_change_different_order(self):
        """Lists with same elements different order should not report changes."""
        desired = {"tags": ["a", "b"]}
        current = {"tags": ["b", "a"]}
        assert recursive_diff(desired, current) is None

    def test_list_of_dicts_change(self):
        """List of dicts with changes should be detected."""
        desired = {"items": [{"id": 1}]}
        current = {"items": [{"id": 2}]}
        diff = recursive_diff(desired, current)
        assert diff == {"items": {"desired": [{"id": 1}], "current": [{"id": 2}]}}

    def test_list_of_dicts_order_matters(self):
        """List of dicts - order matters."""
        desired = {"items": [{"id": 1}, {"id": 2}]}
        current = {"items": [{"id": 2}, {"id": 1}]}
        diff = recursive_diff(desired, current)
        assert diff is not None

    def test_desired_none(self):
        """None desired should return None."""
        assert recursive_diff(None, {"any": "value"}) is None

    def test_non_dict_comparison(self):
        """Non-dict values should compare directly."""
        assert recursive_diff("new", "old") == {"desired": "new", "current": "old"}
        assert recursive_diff("same", "same") is None

    def test_missing_key_in_current(self):
        """Key in desired but not in current should be detected as change."""
        desired = {"new_key": "value"}
        current = {}
        diff = recursive_diff(desired, current)
        assert diff == {"new_key": {"desired": "value", "current": None}}

    def test_extra_key_in_current_ignored(self):
        """Extra key in current should be ignored (only desired keys compared)."""
        desired = {"keep": "value"}
        current = {"keep": "value", "extra": "ignored"}
        assert recursive_diff(desired, current) is None

    def test_nested_dict_missing_in_current(self):
        """Nested dict missing in current should handle empty dict."""
        desired = {"config": {"setting": "value"}}
        current = {}
        diff = recursive_diff(desired, current)
        assert diff == {"config": {"setting": {"desired": "value", "current": None}}}

    def test_empty_list_change(self):
        """Empty list to non-empty should be detected."""
        desired = {"items": ["a"]}
        current = {"items": []}
        diff = recursive_diff(desired, current)
        assert diff == {"items": {"desired": ["a"], "current": []}}

    def test_type_change(self):
        """Type change should be detected."""
        desired = {"value": "string"}
        current = {"value": 123}
        diff = recursive_diff(desired, current)
        assert diff == {"value": {"desired": "string", "current": 123}}

    def test_boolean_change(self):
        """Boolean changes should be detected."""
        desired = {"enabled": True}
        current = {"enabled": False}
        diff = recursive_diff(desired, current)
        assert diff == {"enabled": {"desired": True, "current": False}}

    def test_null_to_value_change(self):
        """None to value change should be detected."""
        desired = {"value": "something"}
        current = {"value": None}
        diff = recursive_diff(desired, current)
        assert diff == {"value": {"desired": "something", "current": None}}


# =============================================================================
# Tests for RemnawaveClient
# =============================================================================


class TestRemnawaveClient:
    """Test cases for RemnawaveClient class."""

    def test_init_strips_trailing_slash(self):
        """Client should strip trailing slash from API URL."""
        client = RemnawaveClient("https://api.example.com/", "token123")
        assert client.api_url == "https://api.example.com"

    def test_init_preserves_url_without_slash(self):
        """Client should preserve URL without trailing slash."""
        client = RemnawaveClient("https://api.example.com", "token123")
        assert client.api_url == "https://api.example.com"

    def test_init_stores_token(self):
        """Client should store API token."""
        client = RemnawaveClient("https://api.example.com", "my-secret-token")
        assert client.api_token == "my-secret-token"


class TestRemnawaveClientGetAll:
    """Test cases for RemnawaveClient.get_all() method."""

    def test_extracts_list_from_nested_response(self, mocker):
        """get_all should extract list from nested response structure."""
        client = RemnawaveClient("https://api.example.com", "token")
        mock_response = {
            "response": {
                "total": 2,
                "items": [{"id": 1}, {"id": 2}],
            }
        }
        mocker.patch.object(client, "_request", return_value=mock_response)

        result = client.get_all("/api/test")
        assert result == [{"id": 1}, {"id": 2}]

    def test_extracts_list_with_explicit_key(self, mocker):
        """get_all should use explicit list_key when provided."""
        client = RemnawaveClient("https://api.example.com", "token")
        mock_response = {
            "response": {
                "total": 2,
                "nodes": [{"name": "node1"}, {"name": "node2"}],
            }
        }
        mocker.patch.object(client, "_request", return_value=mock_response)

        result = client.get_all("/api/nodes", list_key="nodes")
        assert result == [{"name": "node1"}, {"name": "node2"}]

    def test_returns_direct_list_response(self, mocker):
        """get_all should handle response that is directly a list."""
        client = RemnawaveClient("https://api.example.com", "token")
        mock_response = {"response": [{"id": 1}, {"id": 2}]}
        mocker.patch.object(client, "_request", return_value=mock_response)

        result = client.get_all("/api/test")
        assert result == [{"id": 1}, {"id": 2}]

    def test_returns_empty_list_on_null_response(self, mocker):
        """get_all should return empty list when response is null."""
        client = RemnawaveClient("https://api.example.com", "token")
        mocker.patch.object(client, "_request", return_value=None)

        result = client.get_all("/api/test")
        assert result == []

    def test_returns_inner_dict_when_no_list(self, mocker):
        """get_all should return inner dict if no list found."""
        client = RemnawaveClient("https://api.example.com", "token")
        mock_response = {"response": {"key": "value", "other": "data"}}
        mocker.patch.object(client, "_request", return_value=mock_response)

        result = client.get_all("/api/test")
        assert result == {"key": "value", "other": "data"}


class TestRemnawaveClientGetOne:
    """Test cases for RemnawaveClient.get_one() method."""

    def test_returns_resource(self, mocker):
        """get_one should return the resource from response."""
        client = RemnawaveClient("https://api.example.com", "token")
        mock_response = {"response": {"uuid": "123", "name": "test"}}
        mocker.patch.object(client, "_request", return_value=mock_response)

        result = client.get_one("/api/test/{uuid}", "123")
        assert result == {"uuid": "123", "name": "test"}

    def test_replaces_uuid_in_path(self, mocker):
        """get_one should replace {uuid} placeholder in path."""
        client = RemnawaveClient("https://api.example.com", "token")
        mock_request = mocker.patch.object(
            client, "_request", return_value={"response": {}}
        )

        client.get_one("/api/resources/{uuid}", "abc-123")
        mock_request.assert_called_once_with("GET", "/api/resources/abc-123")

    def test_returns_none_on_404(self, mocker):
        """get_one should return None when resource not found (404)."""
        client = RemnawaveClient("https://api.example.com", "token")
        mocker.patch.object(
            client, "_request", side_effect=Exception("API request failed (404): Not found")
        )

        result = client.get_one("/api/test/{uuid}", "123")
        assert result is None

    def test_returns_none_on_not_found_message(self, mocker):
        """get_one should return None when error contains 'not found'."""
        client = RemnawaveClient("https://api.example.com", "token")
        mocker.patch.object(
            client, "_request", side_effect=Exception("Resource not found")
        )

        result = client.get_one("/api/test/{uuid}", "123")
        assert result is None

    def test_raises_on_other_errors(self, mocker):
        """get_one should raise exception for non-404 errors."""
        client = RemnawaveClient("https://api.example.com", "token")
        mocker.patch.object(
            client, "_request", side_effect=Exception("API request failed (500): Server error")
        )

        with pytest.raises(Exception) as exc_info:
            client.get_one("/api/test/{uuid}", "123")
        assert "500" in str(exc_info.value)


class TestRemnawaveClientCreate:
    """Test cases for RemnawaveClient.create() method."""

    def test_creates_resource(self, mocker):
        """create should POST data and return response."""
        client = RemnawaveClient("https://api.example.com", "token")
        mock_response = {"response": {"uuid": "new-123", "name": "created"}}
        mock_request = mocker.patch.object(client, "_request", return_value=mock_response)

        data = {"name": "test"}
        result = client.create("/api/test", data)

        mock_request.assert_called_once_with("POST", "/api/test", data)
        assert result == {"uuid": "new-123", "name": "created"}

    def test_returns_raw_response_without_wrapper(self, mocker):
        """create should return raw response if no 'response' wrapper."""
        client = RemnawaveClient("https://api.example.com", "token")
        mock_response = {"uuid": "123"}
        mocker.patch.object(client, "_request", return_value=mock_response)

        result = client.create("/api/test", {"name": "test"})
        assert result == {"uuid": "123"}


class TestRemnawaveClientUpdate:
    """Test cases for RemnawaveClient.update() method."""

    def test_updates_resource_with_uuid(self, mocker):
        """update should PATCH data with UUID replacement."""
        client = RemnawaveClient("https://api.example.com", "token")
        mock_response = {"response": {"uuid": "123", "name": "updated"}}
        mock_request = mocker.patch.object(client, "_request", return_value=mock_response)

        data = {"name": "updated"}
        result = client.update("/api/test/{uuid}", data, resource_id="123")

        mock_request.assert_called_once_with("PATCH", "/api/test/123", data)
        assert result == {"uuid": "123", "name": "updated"}

    def test_updates_resource_without_uuid(self, mocker):
        """update should use path as-is when no resource_id provided."""
        client = RemnawaveClient("https://api.example.com", "token")
        mock_response = {"response": {"name": "updated"}}
        mock_request = mocker.patch.object(client, "_request", return_value=mock_response)

        data = {"name": "updated"}
        result = client.update("/api/test/static", data)

        mock_request.assert_called_once_with("PATCH", "/api/test/static", data)
        assert result == {"name": "updated"}


class TestRemnawaveClientDelete:
    """Test cases for RemnawaveClient.delete() method."""

    def test_deletes_resource(self, mocker):
        """delete should DELETE with UUID replacement."""
        client = RemnawaveClient("https://api.example.com", "token")
        mock_request = mocker.patch.object(client, "_request", return_value=None)

        client.delete("/api/test/{uuid}", "123")

        mock_request.assert_called_once_with("DELETE", "/api/test/123")


# =============================================================================
# Tests for resolve_config_profile_uuid()
# =============================================================================


class TestResolveConfigProfileUuid:
    """Test cases for resolve_config_profile_uuid() function."""

    def test_finds_profile_by_name(self, mocker):
        """resolve_config_profile_uuid should find profile by name."""
        client = RemnawaveClient("https://api.example.com", "token")
        profiles = [
            {"uuid": "uuid-1", "name": "profile-1"},
            {"uuid": "uuid-2", "name": "profile-2"},
        ]
        mocker.patch.object(client, "get_all", return_value=profiles)

        result = resolve_config_profile_uuid(client, "profile-2")
        assert result == "uuid-2"

    def test_returns_none_when_not_found(self, mocker):
        """resolve_config_profile_uuid should return None when profile not found."""
        client = RemnawaveClient("https://api.example.com", "token")
        profiles = [{"uuid": "uuid-1", "name": "profile-1"}]
        mocker.patch.object(client, "get_all", return_value=profiles)

        result = resolve_config_profile_uuid(client, "nonexistent")
        assert result is None

    def test_handles_empty_profiles(self, mocker):
        """resolve_config_profile_uuid should handle empty profiles list."""
        client = RemnawaveClient("https://api.example.com", "token")
        mocker.patch.object(client, "get_all", return_value=[])

        result = resolve_config_profile_uuid(client, "any-name")
        assert result is None


# =============================================================================
# Tests for resolve_inbound_uuids()
# =============================================================================


class TestResolveInboundUuids:
    """Test cases for resolve_inbound_uuids() function."""

    def test_resolves_single_tag(self, mocker):
        """resolve_inbound_uuids should resolve single tag to UUID."""
        client = RemnawaveClient("https://api.example.com", "token")
        inbounds = [
            {"uuid": "inb-1", "tag": "vless-in"},
            {"uuid": "inb-2", "tag": "vmess-in"},
        ]
        mocker.patch.object(client, "get_all", return_value=inbounds)

        result = resolve_inbound_uuids(client, "profile-uuid", ["vless-in"])
        assert result == ["inb-1"]

    def test_resolves_multiple_tags(self, mocker):
        """resolve_inbound_uuids should resolve multiple tags in order."""
        client = RemnawaveClient("https://api.example.com", "token")
        inbounds = [
            {"uuid": "inb-1", "tag": "vless-in"},
            {"uuid": "inb-2", "tag": "vmess-in"},
            {"uuid": "inb-3", "tag": "trojan-in"},
        ]
        mocker.patch.object(client, "get_all", return_value=inbounds)

        result = resolve_inbound_uuids(client, "profile-uuid", ["vmess-in", "vless-in"])
        assert result == ["inb-2", "inb-1"]

    def test_raises_on_missing_tag(self, mocker):
        """resolve_inbound_uuids should raise ValueError when tag not found."""
        client = RemnawaveClient("https://api.example.com", "token")
        inbounds = [{"uuid": "inb-1", "tag": "vless-in"}]
        mocker.patch.object(client, "get_all", return_value=inbounds)

        with pytest.raises(ValueError) as exc_info:
            resolve_inbound_uuids(client, "profile-uuid", ["nonexistent"])
        assert "Inbound 'nonexistent' not found" in str(exc_info.value)

    def test_handles_empty_tags_list(self, mocker):
        """resolve_inbound_uuids should return empty list for empty tags."""
        client = RemnawaveClient("https://api.example.com", "token")
        mocker.patch.object(client, "get_all", return_value=[])

        result = resolve_inbound_uuids(client, "profile-uuid", [])
        assert result == []

    def test_calls_correct_api_path(self, mocker):
        """resolve_inbound_uuids should call correct API path with profile UUID."""
        client = RemnawaveClient("https://api.example.com", "token")
        mock_get_all = mocker.patch.object(client, "get_all", return_value=[])

        resolve_inbound_uuids(client, "my-profile-uuid", [])
        mock_get_all.assert_called_once_with("/api/config-profiles/my-profile-uuid/inbounds")


# =============================================================================
# Tests for READ_ONLY_FIELDS constant
# =============================================================================


class TestReadOnlyFields:
    """Test that READ_ONLY_FIELDS contains expected fields."""

    def test_contains_uuid(self):
        """READ_ONLY_FIELDS should contain uuid."""
        assert "uuid" in READ_ONLY_FIELDS

    def test_contains_timestamps(self):
        """READ_ONLY_FIELDS should contain timestamp fields."""
        assert "createdAt" in READ_ONLY_FIELDS
        assert "updatedAt" in READ_ONLY_FIELDS

    def test_contains_connection_status_fields(self):
        """READ_ONLY_FIELDS should contain connection status fields."""
        assert "isConnected" in READ_ONLY_FIELDS
        assert "isConnecting" in READ_ONLY_FIELDS
        assert "isDisabled" in READ_ONLY_FIELDS

    def test_contains_node_runtime_fields(self):
        """READ_ONLY_FIELDS should contain node runtime fields."""
        assert "xrayVersion" in READ_ONLY_FIELDS
        assert "usersOnline" in READ_ONLY_FIELDS
        assert "isXrayRunning" in READ_ONLY_FIELDS
        assert "cpuCount" in READ_ONLY_FIELDS
        assert "cpuModel" in READ_ONLY_FIELDS
        assert "totalRam" in READ_ONLY_FIELDS
        assert "publicIp" in READ_ONLY_FIELDS

    def test_contains_active_inbounds(self):
        """READ_ONLY_FIELDS should contain activeInbounds (API quirk)."""
        assert "activeInbounds" in READ_ONLY_FIELDS

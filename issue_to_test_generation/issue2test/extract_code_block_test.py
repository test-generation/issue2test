from tools.extract_code_block import extract_code_block

def basic_python_block():
    text = """
    ```python
    print("Hello, world!")
    ```
    """
    expected = '    print("Hello, world!")'
    result = extract_code_block(text)
    print("test_basic_python_block:", "PASS" if result == expected else f"FAIL (expected: {repr(expected)}, got: {repr(result)})")

def basic_block_without_language():
    text = """
    ```
    print("Hello, world!")
    ```
    """
    expected = '    print("Hello, world!")'
    result = extract_code_block(text)
    print("test_basic_block_without_language:", "PASS" if result == expected else f"FAIL (expected: {repr(expected)}, got: {repr(result)})")

def no_code_block():
    text = "This is just some text without any code blocks."
    expected = ""
    result = extract_code_block(text)
    print("test_no_code_block:", "PASS" if result == expected else f"FAIL (expected: {repr(expected)}, got: {repr(result)})")

def multiple_code_blocks():
    text = """
    ```python
    print("First block")
    ```
    
    Some explanation text here.

    ```python
    print("Second block")
    ```
    """
    expected = '    print("First block")'
    result = extract_code_block(text)
    print("test_multiple_code_blocks:", "PASS" if result == expected else f"FAIL (expected: {repr(expected)}, got: {repr(result)})")

def code_with_extra_text():
    text = """
    This is some explanation.

    ```python
    print("Code inside block")
    ```

    More explanation after the code.
    """
    expected = '    print("Code inside block")'
    result = extract_code_block(text)
    print("test_code_with_extra_text:", "PASS" if result == expected else f"FAIL (expected: {repr(expected)}, got: {repr(result)})")

def empty_code_block():
    text = """
    ```python
    ```
    """
    expected = ""
    result = extract_code_block(text)
    print("test_empty_code_block:", "PASS" if result == expected else f"FAIL (expected: {repr(expected)}, got: {repr(result)})")

def code_block_with_blank_lines():
    text = """
    ```python

    print("Code with blank lines before and after")

    
    ```
    """
    expected = '\n    print("Code with blank lines before and after")'
    result = extract_code_block(text)
    print("test_code_block_with_blank_lines:", "PASS" if result == expected else f"FAIL (expected: {repr(expected)}, got: {repr(result)})")

def code_block_with_indentation():
    text = """
    ```python
        def function():
            return "Indented code"
    ```
    """
    expected = '        def function():\n            return "Indented code"'
    result = extract_code_block(text)
    print("test_code_block_with_indentation:", "PASS" if result == expected else f"FAIL (expected: {repr(expected)}, got: {repr(result)})")

def code_block_with_special_characters():
    text = """
    ```python
    print("Special characters: !@#$%^&*()_+{}:\"<>?")
    ```
    """
    # Adjust expected output to match Python’s interpreted string format
    expected = '    print("Special characters: !@#$%^&*()_+{}:"<>?")'
    result = extract_code_block(text)
    print("test_code_block_with_special_characters:", "PASS" if result == expected else f"FAIL (expected: {repr(expected)}, got: {repr(result)})")

def code_block_with_only_start_marker():
    text = """
    ```python
    print("No end marker"""
    expected = ""
    result = extract_code_block(text)
    print("test_code_block_with_only_start_marker:", "PASS" if result == expected else f"FAIL (expected: {repr(expected)}, got: {repr(result)})")

def code_block_with_only_end_marker():
    text = """
    ```
    """
    expected = ""
    result = extract_code_block(text)
    print("test_code_block_with_only_end_marker:", "PASS" if result == expected else f"FAIL (expected: {repr(expected)}, got: {repr(result)})")

def long_code_block():
    text = """
    ```python
    import unittest
    import requests
    from requests.compat import builtin_str

    class TestRequestsMethodHandling(unittest.TestCase):

        def setUp(self):
            self.session = requests.Session()

        def tearDown(self):
            self.session.close()

        def test_method_as_binary_string(self):
            # This test should fail initially because the method is not handled correctly
            # when passed as a binary string.
            method = b'GET'
            url = 'http://httpbin.org/get'
            
            # Prepare a request with a binary method
            req = requests.Request(method=builtin_str(method), url=url)
            prepared = self.session.prepare_request(req)
            
            # Send the request
            response = self.session.send(prepared)
            
            # Assert that the response is successful
            self.assertEqual(response.status_code, 200)

    if __name__ == '__main__':
        unittest.main()
    ```
    
    This test case is designed to fail initially because the requests library does not correctly handle HTTP methods passed as binary strings. Once the issue is fixed, the test should pass, confirming that the method is correctly interpreted and the request is successful.
    """
    expected = """    import unittest
    import requests
    from requests.compat import builtin_str

    class TestRequestsMethodHandling(unittest.TestCase):

        def setUp(self):
            self.session = requests.Session()

        def tearDown(self):
            self.session.close()

        def test_method_as_binary_string(self):
            # This test should fail initially because the method is not handled correctly
            # when passed as a binary string.
            method = b'GET'
            url = 'http://httpbin.org/get'
            
            # Prepare a request with a binary method
            req = requests.Request(method=builtin_str(method), url=url)
            prepared = self.session.prepare_request(req)
            
            # Send the request
            response = self.session.send(prepared)
            
            # Assert that the response is successful
            self.assertEqual(response.status_code, 200)

    if __name__ == '__main__':
        unittest.main()"""

    result = extract_code_block(text)
    print("test_long_code_block:", "PASS" if result == expected else f"FAIL (expected: {repr(expected)}, got: {repr(result)})")

# Manually invoke each test
basic_python_block()
basic_block_without_language()
no_code_block()
multiple_code_blocks()
code_with_extra_text()
empty_code_block()
code_block_with_blank_lines()
code_block_with_indentation()
code_block_with_special_characters()
code_block_with_only_start_marker()
code_block_with_only_end_marker()
long_code_block()

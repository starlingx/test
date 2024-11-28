from keywords.base_keyword import BaseKeyword


def test_pretty_print_none():
    """
    Tests that pretty_print works well with None
    """
    base_keyword = BaseKeyword()
    pretty_text = base_keyword.pretty_print(None)
    assert pretty_text == "None", 'Failed to pretty-print None'


def test_pretty_print_string():
    """
    Tests that pretty_print works well with Strings
    """
    base_keyword = BaseKeyword()
    pretty_text = base_keyword.pretty_print("This Framework is awesome!")
    assert pretty_text == "This Framework is awesome!", 'Failed to pretty-print the string'


def test_pretty_print_int():
    """
    Tests that pretty_print works well with Integers
    """
    base_keyword = BaseKeyword()
    pretty_text = base_keyword.pretty_print(42)
    assert pretty_text == "42", 'Failed to pretty-print the int'


def test_pretty_print_float():
    """
    Tests that pretty_print works well with Floats
    """
    base_keyword = BaseKeyword()
    pretty_text = base_keyword.pretty_print(2.71828)
    assert pretty_text == "2.71828", 'Failed to pretty-print the float'


def test_pretty_print_bool():
    """
    Tests that pretty_print works well with Booleans
    """
    base_keyword = BaseKeyword()
    pretty_text = base_keyword.pretty_print(True)
    assert pretty_text == "True", 'Failed to pretty-print the boolean'


def test_pretty_print_list():
    """
    Tests that pretty_print works well with List
    """
    base_keyword = BaseKeyword()
    pretty_text = base_keyword.pretty_print(["This", "Framework", "Is", "Awesome"])
    assert pretty_text == "[This, Framework, Is, Awesome]", 'Failed to pretty-print the List'


def test_pretty_print_tuple():
    """
    Tests that pretty_print works well with Tuples
    """
    base_keyword = BaseKeyword()
    pretty_text = base_keyword.pretty_print(("This", "Framework", "Is", "Awesome"))
    assert pretty_text == "(This, Framework, Is, Awesome)", 'Failed to pretty-print the Tuple'


def test_pretty_print_dictionary():
    """
    Tests that pretty_print works well with Dictionaries
    """
    base_keyword = BaseKeyword()
    pretty_text = base_keyword.pretty_print({"This Framework": 42, "Is Awesome": True})
    assert (
        pretty_text == "{This Framework:42, Is Awesome:True}"
    ), 'Failed to pretty-print the Dictionary'


def test_pretty_print_complex_dictionary():
    """
    Tests that pretty_print works well with a Dictionary containing complex objects
    """

    inner_dictionary = {"Key1": "Value", "Key2": "Door"}
    dictionary = {"Embedded": ["These", "Are", "List", "Items"], "Dictionary": inner_dictionary}

    base_keyword = BaseKeyword()
    pretty_text = base_keyword.pretty_print({"None": None, 1: ["One", 2, False], "Two": dictionary})

    first = "None:None"
    second = "1:[One, 2, False]"
    third = "Two:{Embedded:[These, Are, List, Items], Dictionary:{Key1:Value, Key2:Door}}"

    assert (
        pretty_text == "{" + f"{first}, {second}, {third}" + "}"
    ), 'Failed to pretty-print the Dictionary'

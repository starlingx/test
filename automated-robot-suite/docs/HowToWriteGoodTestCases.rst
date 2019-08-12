.. default-role:: code

======================================================================
How to write good test cases using Robot Framework for stx-test-suite
======================================================================

.. contents:: Table of contents:
   :local:
   :depth: 2


Introduction
============

- These are high-level guidelines for writing good test cases using Robot
  Framework. It is based on the official `how to`__ file
  for Robot Framework.

__ https://github.com/robotframework/HowToWriteGoodTestCases/blob/master/
   HowToWriteGoodTestCases.rst

  - How to actually interact with the system under test is out of
    the scope of this document.

- Most important guideline is keeping test cases as easy to understand as
  possible for people familiar with the domain.

  - This typically also eases maintenance.

Naming
======

Test suite names
----------------

- Suite names should be as descriptive as possible.

- Names are created automatically from file or directory names:

  - Extensions are stripped.
  - Underscores are converted to spaces.
  - If name is all lower case, words are capitalized.

- Names can be relatively long, but overly long names are not convenient for
  the file system.

- The name of the top level suite can be overridden from the command line
  using the `--name` option if needed.

Examples:

- `login_tests.robot` -> `Login Tests`
- `IP_v4_and_v6` -> `IP v4 and v6`


Test case names
---------------

- Test names should be descriptive like the suite names.

- If a suite contains many similar tests and is well named,
  test names can be shorter.

- Name is exactly the same as you specified in the test case file without any
  conversion.

For example, if we have tests related to invalid login in a file
`invalid_login.robot`, these would be OK test case names:

.. code:: robotframework

  *** Test Cases ***
  Empty Password
  Empty Username
  Empty Username And Password
  Invalid Username
  Invalid Password
  Invalid Username And Password

These names would be somewhat long:

.. code:: robotframework

  *** Test Cases ***
  Login With Empty Password Should Fail
  Login With Empty Username Should Fail
  Login With Empty Username And Password Should Fail
  Login With Invalid Username Should Fail
  Login With Invalid Password Should Fail
  Login With Invalid Username And Invalid Password Should Fail


Keyword names
-------------

- Keyword names should be descriptive and clear.

- Should explain what the keyword does, not how it does its task(s).

- Very different abstraction levels (e.g. `Input Text` or `Administrator
  logs into system`).

- There is no clear guideline on whether a keyword should be fully title cased
  or have only the first letter be capitalized.

  - Title casing is often used when the keyword name is short
    (e.g. `Input Text`).
  - Capitalizing just the first letter typically works better with keywords
    that are like sentences (e.g. `Administrator logs into system`). These
    type of keywords are often higher level.

Good:

.. code:: robotframework

  *** Keywords ***
  Login With Valid Credentials

Bad:

.. code:: robotframework

  *** Keywords ***
  Input Valid Username And Valid Password And Click Login Button


Naming setup and teardown
-------------------------

- Try to use name that describes what is done.

  - Possibly use an existing keyword.

- More abstract names are acceptable if a setup or teardown contains unrelated
  steps.

  - Listing steps in name is duplication and a maintenance problem
    (e.g. `Login to system, add user, activate alarms and check balance`).

  - Often better to use something generic (e.g. `Initialize system`).

- BuiltIn keyword `Run Keywords`__ can work well if keywords implementing lower
  level steps already exist.

  - Not reusable so best used when the setup or teardown scenario is
    needed only once.

- Everyone working with these tests should always understand what a setup or
  teardown does.

Good:

.. code:: robotframework

  *** Settings ***
  Suite Setup     Initialize System

Good (if only used once):

.. code:: robotframework

  *** Settings ***
  Suite Setup     Run Keywords
  ...             Login To System    AND
  ...             Add User           AND
  ...             Activate Alarms    AND
  ...             Check Balance

Bad:

.. code:: robotframework

    *** Settings ***
    Suite Setup    Login To System, Add User, Activate Alarms And Check Balance

__ http://robotframework.org/robotframework/latest/libraries/
   BuiltIn.html#Run%20Keywords


Documentation
=============

Test suite documentation
------------------------

- Add overall documentation to test case files is mandatory.

- Should contain background information, why tests are created, notes about
  execution environment, etc.

- Do not just repeat test suite name.

- Do not include too much details about test cases.

  - Tests should be clear enough to understand alone.
  - Duplicate information is waste and maintenance problem.

- Documentation can contain links to more information.

- Consider using `test suite metadata`__ if you need to document information
  represented as name-value pairs (e.g. `Version: 1.0` or `OS: Linux`).

__ http://robotframework.org/robotframework/latest/
   RobotFrameworkUserGuide.html#free-test-suite-metadata

- Documentation and metadata of the top level suite can be set from the
  command line using `--doc` and `--metadata` options, respectively.

Good:

.. code:: robotframework

  *** Settings ***
  Documentation    Tests to verify that account withdrawals succeed and
  ...              fail correctly depending from users account balance
  ...              and account type dependent rules.
  ...              See http://internal.example.com/docs/abs.pdf
  Metadata         Version    0.1

Bad (especially if suite is named well like `account_withdrawal.robot`):

.. code:: robotframework

  *** Settings ***
  Documentation    Tests Account Withdrawal.


Test case documentation
-----------------------

- Test should have documentation. Only repeating the name of the test is not
  valid.

  - Test case structure should be clear enough without documentation or other
    comments.

- Tags are generally more flexible and provide more functionality (statistics,
  include/exclude, etc.) than documentation. Tags for type of configuration
  are mandatory.

.. code:: robotframework

  [Tags]    Simplex    Duplex    MN-Local    MN-External

Good:

.. code:: robotframework

  *** Test Cases ***
  Create Flavors for Cirros Instances
  [Tags]    Simplex    Duplex    MN-Local    MN-External
  [Documentation]    Create flavors with or without properties to be used
  ...    to launch Cirros instances.
  ${properties}=    Catenate    ${flavor_property_1}    ${flavor_property_2}
  Create Flavor    ${flavor_ram}    ${flavor_vcpus}    ${flavor_disk}
  ...    ${flavor_name_1}
  Create Flavor    ${flavor_ram}    ${flavor_vcpus}    ${flavor_disk}
  ...    ${properties}    ${flavor_name_2}

Bad:

.. code:: robotframework

  *** Test Cases ***
  Create Flavors for Cirros Instances
  [Documentation]    Create flavors giving a ram, vcpus and disk with or
  ...    without properties o be used to launch Cirros instances on Simplex,
  ...    Duplex or Multinode configuration for SaTarlingX deployment.
  ...    All is done calling a keyword called Create Flavor with some
  ...    parameters ... etc
  [Tags]    Simplex    Duplex    MN-Local    MN-External
  ${properties}=    Catenate    ${flavor_property_1}    ${flavor_property_2}
  Create Flavor    ${flavor_ram}    ${flavor_vcpus}    ${flavor_disk}
  ...    ${flavor_name_1}
  Create Flavor    ${flavor_ram}    ${flavor_vcpus}    ${flavor_disk}
  ...    ${properties}    ${flavor_name_2}


User keyword documentation
--------------------------

- Its important document what keyword is doing.

- Important usage is documenting arguments and return values.

- Shown in resource file documentation generated with Libdoc__ and editors
  such as RIDE__ can show it in keyword completion and elsewhere.

__ http://robotframework.org/robotframework/#built-in-tools
__ https://github.com/robotframework/RIDE


Test suite structure
====================
- All test should be placed under Test/X directory where X indicates the Domain
  where Test Case belongs

- Tests in a suite should be related to each other.

  - Common setup and/or teardown is often a good indicator.

- Should not have too many tests (max 10) in one file unless they are
  `data-driven tests`_.

- Tests should be independent. Initialization using setup/teardown.

- Sometimes dependencies between tests cannot be avoided.

  - For example, it can take too much time to initialize all tests separately.
  - Never have long chains of dependent tests.
  - Consider verifying the status of the previous test using the built-in
    `${PREV TEST STATUS}` variable.

 - We try to avoid the usage of keywords inside of a Test Suite unless they are
   very specific to the test cases, if a keyword is designed and is generic,
   this jeyword should be placed under Resources/ directory.

.. code:: robotframework

    *** Keywords ***
    Run Command
    [Arguments]    ${cmd}    ${fail_if_error}=False    ${timeout}=${TIMEOUT}
    [Documentation]    Execute a command on controller over ssh connection
    ...    keeping environment visible to the subsequent keywords.Also allows
    ...    the keyword to fail if there is an error, by default this
    ...    keyword will not fail and will return the stderr.


Test case structure
===================

- Test case should be easy to understand.

- Test case should be tagged and documented

- One test case should be testing one thing.

  - *Things* can be small (part of a single feature) or large (end-to-end).

- Select suitable abstraction level.

  - Use abstraction level consistently (single level of abstraction principle).
  - Do not include unnecessary details on the test case level.

- We are using an strategy of `Workflow tests`_ for our development, please
  follow the rules

- Try to not exceed 79 characters when possible, if it nos possible or the
  test case get not esasy to read 99 chars are accepted.

Workflow tests
--------------

- Generally have these phases:

  - Precondition (optional, often in setup)
  - Action (do something to the system)
  - Verification (validate results, mandatory)
  - Cleanup (optional, always in teardown to make sure it is executed)

- Keywords describe what a test does.

  - Use clear keyword names and suitable abstraction level.
  - Should contain enough information to run manually.
  - Should never need documentation or commenting to explain what the
    test does.

- Different tests can have different abstraction levels.

  - Tests for a detailed functionality are more precise.
  - End-to-end tests can be on very high level.
  - One test should use only one abstraction level

- Different styles:

  - More technical tests for lower level details and integration tests.
  - "Executable specifications" act as requirements.
  - Use domain language.
  - Everyone (including customer and/or product owner) should
    always understand.

- Try to not use complex logic on the test case level.

  - No for loops or if/else constructs as much as possible.
  - Use variable assignments with care.
  - Test cases should not look like scripts!

- Max 15 steps, preferably less.

Example using "normal" keyword-driven style:

.. code:: robotframework

  *** Test Cases ***
  Valid Login
      Open Browser To Login Page
      Input Username    demo
      Input Password    mode
      Submit Credentials
      Welcome Page Should Be Open

User keywords
=============

- Should be easy to understand.

  - Same rules as with workflow tests.

- Different abstraction levels.

- Can contain some programming logic (for loops, if/else).

  - Especially on lower level keywords.
  - Complex logic in libraries rather than in user keywords.

- Try to not exceed 79 characters when possible, if it nos possible or the
  keyword becomes not esasy to read 99 chars are accepted.


Variables
=========

- Encapsulate long and/or complicated values.

- Pass information between keywords.


Variable naming
---------------

- Clear but not too long names.

- Use case consistently:

  - Lower case with local variables only available inside a certain scope.
  - Upper case with others (global, suite or test level).
  - Both space and underscore can be used as a word separator.

- Recommended to also list variables that are set dynamically in the variable
  table.

  - Set typically using BuiltIn keyword `Set Suite Variable`__.
  - The initial value should explain where/how the real value is set.

Example:

.. code:: robotframework

  *** Settings ***
  Suite Setup       Set Active User

  *** Variables ***
  # Default system address. Override when tested agains other instances.
  ${SERVER URL}     http://sre-12.example.com/
  ${USER}           Actual value set dynamically at suite setup

  *** Keywords ***
  Set Active User
      ${USER} =    Get Current User    ${SERVER URL}
      Set Suite Variable    ${USER}

__ http://robotframework.org/robotframework/latest/libraries/
   BuiltIn.html#Set%20Suite%20Variable


Passing and returning values
----------------------------

- Common approach is to return values from keywords, assign them to variables
  and then pass them as arguments to other keywords.

  - Clear and easy to follow approach.
  - Allows creating independent keywords and facilitates re-use.
  - Looks like programming and thus not so good on the test case level.

- Alternative approach is storing information in a library or using the BuiltIn
  `Set Test Variable`__ keyword.

  - Avoid programming style on the test case level as much as possible.
  - Can be more complex to follow and make reusing keywords harder.

__ http://robotframework.org/robotframework/latest/libraries/
   BuiltIn.html#Set%20Test%20Variable

Good for in suite keywords:

.. code:: robotframework

  *** Test Cases ***
  Withdraw From Account
      Withdraw From Account    $50
      Withdraw Should Have Succeeded

  *** Keywords ***
  Withdraw From Account
      [Arguments]    ${amount}
      ${STATUS} =    Withdraw From User Account    ${USER}    ${amount}
      Set Test Variable    ${STATUS}

  Withdraw Should Have Succeeded
      Should Be Equal    ${STATUS}   SUCCESS

Good for generic keywords:

.. code:: robotframework

  *** Test Cases ***
  Withdraw From Account
      ${status} =    Withdraw From Account    $50
      Withdraw Should Have Succeeded    ${status}

  *** Keywords ***
  Withdraw From Account
      [Arguments]    ${amount}
      ${status} =    Withdraw From User Account    ${USER}    ${amount}
      [Return]    ${status}

  Withdraw Should Have Succeeded
      [Arguments]    ${status}
      Should Be Equal     ${status}    SUCCESS


Avoid sleeping
==============

- Sleeping is a very fragile way to synchronize tests.

- Safety margins cause too long sleeps on average.

- Instead of sleeps, use keyword that polls has a certain action occurred.

  - Keyword names often starts with `Wait ...`.
  - Should have a maximum time to wait.
  - Possible to wrap other keywords inside the BuiltIn keyword
    `Wait Until Keyword Succeeds`__.

- Sometimes sleeping is the easiest solution.

  - Always use with care.
  - Never use in user keywords that are used often by tests or other keywords.

- Can be useful in debugging to stop execution.

  - `Dialogs library`__ often works better.

__ http://robotframework.org/robotframework/latest/libraries/
   BuiltIn.html#Wait%20Until%20Keyword%20Succeeds
__ http://robotframework.org/robotframework/latest/libraries/Dialogs.html

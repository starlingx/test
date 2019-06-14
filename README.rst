========
stx-test
========

StarlingX Test repository for manual and automated test cases.


Contribute
----------

- Clone the repo
- Gerrit hook needs to be added for code review purpose.

.. code-block:: bash

    # Generate a ssh key if needed
    ssh-keygen -t rsa -C "<your email address>"
    ssh-add $private_keyfile_path

    # add ssh key to settings https://review.opendev.org/#/q/project:starlingx/test
    cd <stx-test repo>
    git remote add gerrit ssh://<your gerrit username>@review.opendev.org/starlingx/test.git
    git review -s

- When you are ready, create your commit with detailed commit message, and submit for review.
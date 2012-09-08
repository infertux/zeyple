#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from mock import Mock
import os
import shutil
from zeyple import zeyple

class ZeypleTest(unittest.TestCase):
    def setUp(self):
        shutil.copyfile('tests/zeyple.conf', 'zeyple.conf')
        self.zeyple = zeyple.Zeyple()
        self.zeyple._sendMessage = Mock() # don't try to send emails

    def tearDown(self):
        os.remove('zeyple.conf')

    def test__config(self):
        """Parses the configuration file properly"""

        self.assertEqual(
            self.zeyple._config.get('zeyple', 'log_file'),
           '/tmp/zeyple.log'
        )

    def test__userKey(self):
        """Returns the right ID for the given email address"""

        self.assertIsNone(self.zeyple._userKey('non_existant@example.org'))

        linus_id = "79BE3E4300411886"
        os.system("gpg --recv-keys %s 2> /dev/null" % linus_id)
        self.assertEqual(
            self.zeyple._userKey('torvalds@linux-foundation.org'),
            linus_id
        )

    def test__encrypt(self):
        """Encrypts plain text"""

        encrypted = self.zeyple._encrypt(
            'The key is under the carpet.', ['79BE3E4300411886']
        )
        self.assertTrue(encrypted.startswith(b'-----BEGIN PGP MESSAGE-----'))

    def test_processMessage(self):
        """Calls the sendMessage method"""

        self.zeyple.processMessage("""\
            Received: by example.org (Postfix, from userid 0)
                id DD3B67981178; Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            To: torvalds@linux-foundation.org
            Subject: Hello
            Message-Id: <20120906233537.DD3B67981178@example.org>
            Date: Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            From: root@example.org (root)

            test
        """)

        assert self.zeyple._sendMessage.called


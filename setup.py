# coding: utf-8
#
# Copyright (c) 2014, CGI
# 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright 
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the CGI nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------

# Author: Danny Milsom <danny.milsom@cgi.com>
# Copyright (C) 2014 CGI IT UK Ltd

from setuptools import setup, find_packages

setup(
    name='ProjectMessagePlugin', 
    version=0.1,
    description='Supports the creation of messages shown to project members '
                'inside the web interface.',
    author="Danny Milsom", 
    author_email="danny.milsom@cgi.com",
    license='BSD', 
    url='http://define.primeportal.com/',
    packages = ['projectmessage', 'projectmessage.upgrades'],
    package_data={
        'projectmessage': [
            'htdocs/js/*.js',
            'htdocs/css/*.css',
            'templates/*',
        ]
    },
    test_suite = 'projectmessage.tests.suite',
    entry_points = {
        'trac.plugins': [
            'projectmessage.admin = projectmessage.admin',
            'projectmessage.api = projectmessage.api',
            'projectmessage.models = projectmessage.models',
            'projectmessage.rpc = projectmessage.rpc',
            'projectmessage.web_ui = projectmessage.web_ui',
        ]
    }
)

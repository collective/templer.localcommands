.. contents::

Introduction
============

This package provides the framework for local commands within the templer
system. In order for localcommands to be available to any templer package,
this package must be included.

In general, this is accomplished through an extra for the package, so for 
example if you wish to enable the local commands available for the templates
in the templer.plone package, you would reference the package thus::

    templer.plone[localcommands]

This flexibility allows more advanced users to use lighter, more flexible 
templates, while also supporting new users with templates that help them to 
get started more quickly.

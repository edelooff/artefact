artefact
########

Provides a Python API to query the `Archive of Our Own`_. This has a limited set of features and options, mainly around works and tag searches:

* Search for works using the "Work Search" form/interface or by tag
* Support for logging in, opening up *restricted* works for search
* HTML-processing of search results into individual ``Blurb``s for works
* Optional automated Tag resolution and mapping to their *merged* canonical form
* Responsible crawling of result pages and recovery from rate limting

.. code-block:: python

    from artefact import Artefact

    artefact = Artefact()
    works = artefact.search(
        character_names="Batman",
        language_id="en",
        complete="T",
    )
    work = next(works)
    print(f"{work.title} by {work.author or 'Anonymous'}")


.. _Archive of Our Own: https://archiveofourown.org/
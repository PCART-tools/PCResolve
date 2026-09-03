#!/usr/bin/env python3
## @package ground_truth.probes.scrapping_probe
#  Minimal receiver-ownership probe for BeautifulSoup attribute values.

import inspect


## Return the defining module name for a callable when available.
#  @param value Callable or descriptor to inspect.
#  @return Module name or an empty string.
def _module_name(value):
    module = inspect.getmodule(value)
    return module.__name__ if module is not None else ""


## Verify the callable/result boundary of Tag.get("href").
def probe_tag_get_href_result():
    import bs4
    from bs4 import BeautifulSoup

    tag = BeautifulSoup('<a href="/target">target</a>',
                        'html.parser').a
    link = tag.get('href')

    print("beautifulsoup version:", bs4.__version__)
    print("tag type module:", type(tag).__module__)
    print("Tag.get method module:", _module_name(tag.get))
    print("href result type module:", type(link).__module__)
    print("str.find descriptor owner:",
          getattr(type(link).find, "__objclass__", None))
    print("find bound receiver:", link.find.__self__ is link)

    assert type(tag).__module__.split(".")[0] == "bs4"
    assert _module_name(tag.get).split(".")[0] == "bs4"
    assert type(link) is str
    assert getattr(type(link).find, "__objclass__", None) is str
    assert link.find.__self__ is link


## Run all scrapping ownership probes.
def main():
    probe_tag_get_href_result()
    print("all probes passed")


if __name__ == "__main__":
    main()

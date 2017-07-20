#import argparse
import sys, re

import urllib
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen, Request

from tld import get_tld
from tld.exceptions import TldBadUrl,TldDomainNotFound

# uncomment below if the site you're trying has a newer tld
#from tld.utils import update_tld_names
#update_tld_names()

#
a_tag_pattern = re.compile(b'<a [^>]*href=[\'|"](?!javascript:|#|mailto:)(.*?)[\'"][^>]*?>')

# Don't parse
blacklist = (".jpg", ".jpeg", ".png", ".mp4", ".zip", ".exe", ".pdf", ".txt")

# Set of links found on domain - use dict if you want to catch titles
# as well. Neccessary(?) if you actually wanted to make a sitemap page.
collected = set()
rejected = set()

# The domain to be crawled
domain = ""


def crawl(page, prev=None):
    """ Recursively collect links on a given page.

    prev isn't need and was added later to give some context to certain weird
    results (that were sane, just various bugs on some sites).

    Adds to global set. """
    # Ugly, but constraints.
    global collected
    global rejected
    global domain

    page = page.decode("utf-8")
    url = urlparse(page)
    ###print("Trying: {}".format(page), end='')

    # Check for valid scheme
    if url.scheme not in ("http", "https"):

        if url.scheme == '':
            # try adding https - this is hacky, would do it better usually.
            # parse it again with a scheme --> not sure if needed <<- TODO
            ####print("Attempting to remake URL: {}".format(url))
            _newrl = list(url)
            _newrl[0] = "http"

            page = urlunparse(_newrl)
            url = urlparse(page)
        else:
            ###print('...rejected')
            rejected.add(page)
            return

    if url.netloc == '':
        # if no domain, it should be this domain. (again, hacky :\))
        _newrl = list(url)
        _newrl[1] = domain

        page = urlunparse(_newrl)
        url = urlparse(page)
        ####print("Adding domain to: {}".format(url))


    if url.path.endswith(blacklist):
        ###print('...rejected')
        rejected.add(page)
        return

    # We're allowing subdomains. Would probably add a switch to ensure that's
    # what the user wanted.
    try:
        link_domain = get_tld("{}://{}".format(url.scheme, url.netloc))
    except TldBadUrl as tlde:
        rejected.add(page)
        return
    except TldDomainNotFound as tlde:
        ###print('...rejected')
        rejected.add(page)
        print("This page has a malformed link: {}".format(prev)) # - just figuring out where links were poorly formed
        return

    # Ensure we're still in the same domain.
    # If we weren't allowing subdomains, we'd just compare domain to netloc
    if not link_domain == domain:
        ###print('...rejected')
        rejected.add(page)
        return

    request = Request(page, \
        headers={"User-Agent": "pcooper-spider"})

    try:
        response = urlopen(request)
    except urllib.error.HTTPError:
        ###print('...rejected')
        rejected.add(page)
        return

    # Collect link (even if provided no responseO)
    ###print('...added!')
    collected.add(page)

    if response is not None and response.getcode() == 200:
        links = re.findall(a_tag_pattern, response.read())
        [crawl(l, page) for l in links if l.decode("utf-8") not in collected \
                                      and l.decode("utf-8") not in rejected]


def main(argv=[]):
    # global is ugly ofc. but suits this particular task.
    global collected
    global rejected
    global domain

    try:
        target = argv[argv.index('-d')+1]
    except ValueError as e:
        # arg not in list, just use a default rather than creating an entire
        # help/usage section...but tell them about the -d flag.
        target = "http://deliveryhero.com"
        ###print("Use the -d flag to specify the domain you wish to crawl.")
        ###print("Using deliveryhero.com as a default for now.")

    # Replace below with validate_page
    try:
        url = urlparse(target)
        domain = get_tld("{}://{}".format(url.scheme, url.netloc))
    except:
        ###print("Bad Link")
        return 1

    crawl(target.encode("utf-8"))

    print("\n")
    print("Number of links collected: {}".format(len(collected)))
    print("Number of links rejected: {}".format(len(rejected)))
    print("Displaying Sorted Sitemap...\n")
    output = "\n".join(sorted(collected))
    print(output)

    return 0


if __name__ == "__main__":
    main(sys.argv)

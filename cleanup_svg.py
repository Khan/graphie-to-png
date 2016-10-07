#!/usr/bin/env python

# Adapted from elements of https://github.com/petercollingridge/SVG-Optimiser

import logging
import os
import re
import subprocess

import lxml.etree
import svg.path


_ROOT = os.path.realpath(os.path.dirname(__file__))


def get_tag(element):
    """Get the tag name from an element

    In SVGs, `element.tag` is preceded by the namespace, so it looks like

        {http://www.w3.org/2000/svg}clipPath

    This retrieves the 'clipPath' part
    """
    return element.tag.split('}')[1]


def remove_element(element):
    element.getparent().remove(element)


# Regex for matching clip-path urls
clip_path_url_regex = re.compile(r'url\(\#([^\)]+)\)')


def _run_svgo(svg):
    """Given the contents of an svg, return the svgo-ized contents."""
    p = subprocess.Popen([os.path.join(_ROOT, "node_modules", ".bin", "svgo"),
                          '-i', '-', '-o', '-'],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate(input=svg)
    rc = p.wait()
    if stderr or rc != 0:
        raise RuntimeError('svgo call failed (rc %s): %s' % (rc, stderr))
    return stdout


def _cleanup_clip_paths(tree):
    """Remove duplicate clip paths.

    Every time an element with a clip path is added in Raphael, a new
    clipPath element is created with a unique ID to go along with
    it. This creates a lot of duplicate clip paths.

    To fix this, we remove duplicate clip paths, and fix all references
    to clip-paths to use the fixed-up name.
    """
    clip_paths = {}
    to_remove = []

    for element in tree.iter():
        tag = get_tag(element)

        # We only handle clipPaths with a single 'rect' child for now
        if tag == "clipPath" and len(element.getchildren()) == 1:
            element_id = element.get('id')
            child = element.getchildren()[0]

            if get_tag(child) == "rect":
                clip_def = (child.get('x'),
                            child.get('y'),
                            child.get('height'),
                            child.get('width'),
                            child.get('transform'))
            else:
                continue

            if clip_def in clip_paths:
                # If we've already seen the same clip path, remove the
                # element. We can't actually remove the elements here or
                # the iterator gets messed up, so we add it to a list to
                # remove later
                to_remove.append(element)

            # The first element-id is the one we keep, the rest we delete
            clip_paths.setdefault(clip_def, []).append(element_id)

    for element in to_remove:
        remove_element(element)

    clip_urls = {}

    # Generate a mapping from old ids to remaining ids
    for urls in clip_paths.itervalues():
        # The new url is the first thing in the list
        new_url = urls[0]
        for url in urls[1:]:
            clip_urls[url] = new_url

    # Replace instances of the old ids to the new ones
    for element in tree.iter():
        if "clip-path" in element.keys():
            path = element.get("clip-path")
            match = clip_path_url_regex.match(path)
            if match:
                url = match.group(1)
                if url in clip_urls:
                    element.attrib["clip-path"] = (
                        "url(#" + clip_urls[url] + ")")


def _clip_paths(tree):
    """Clip outrageous values out of paths that rafael creates.

    If you give raphael a function to graph like 2**2**x, it can
    produce an svg path like:
        M104.00000000000148,-172488677.42386922L104.50000000000148,...
    -172,000,000 is not going to fit inside our viewport.  In fact,
    for firefox we have an overflow error and some ugly looking
    lines in random parts of the graph.  For that reason, if a
    path consists entirely of 'M' and 'L' directives, I remove
    all directives at the front and the back of the path that
    have either an X or a Y coordinate that is "way too large".
    """
    MAX = 1000000     # in my tests, firefox does fine with values up to 1M

    for element in tree.iter():
        tag = get_tag(element)
        if tag == "path":
            try:
                # NOTE: This rounds to 1 decimal point, which I guess
                # is fine though svgo would do that for us too.
                path = svg.path.parse_path(element.get("d"))

                # path is now a list of Line's, each Line is a complex
                # number ('real' is x coord and 'complex' is y coord).
                # I use abs() to get the euclidian distance for pruning.
                while (path and
                       max(abs(path[0].start), abs(path[0].end)) > MAX):
                    del path[0]
                while (path and
                       max(abs(path[-1].start), abs(path[-1].end)) > MAX):
                    del path[-1]

                element.set("d", path.d())
            except:
                # Sometimes, svg.path fails to re-generate the path if it's
                # strange. We ignore this and leave the original path.
                continue


def cleanup_svg(svgdata):
    """Run all of the cleanup functions on an svg file

    Read in an SVG file as a string, decode it using lxml, run all of the
    cleanup functions on it, and re-encode it.
    """
    try:
        # We do our passes first, then the svgo pass, since it's easier
        # to modify the unoptimized svg than the optimized.

        tree = lxml.etree.fromstring(svgdata)
        _cleanup_clip_paths(tree)
        _clip_paths(tree)
        new_svgdata = lxml.etree.tostring(tree)

        return _run_svgo(new_svgdata)

    except Exception:
        logging.exception("Cleanup svg failed")


if __name__ == '__main__':
    import sys
    print cleanup_svg(sys.stdin.read())

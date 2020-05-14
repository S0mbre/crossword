# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.graphs
# Used to display statistics for the current crossword in the web browser
# using the Altair package. See [Altair docs](https://altair-viz.github.io/).
import pandas as pd
import altair as alt

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

## Converts a Python dictionary into a pandas `DataFrame` or altair `NamedData`
# @param panda `bool` `True` to convert to a pandas `DataFrame` object; 
# `False` to convert to a `NamedData` object
# @param xy `bool` if `True`, the `data` dict will be aggregated into a dict with
# 2 keys: `x`: all keys and `y`: all values; e.g. if `data` is originally:
# ```{'a': 1, 'b': 2, 'c': 3}```
# it will be transformed into:
# ```{'x': ['a', 'b', 'c'], 'y': [1, 2, 3]}```
# @returns `DataFrame`|`NamedData` converted object
def data_from_dict(data, panda=True, xy=True):
    if xy: data = {'x': list(data.keys()), 'y': list(data.values())}        
    return pd.DataFrame(data=data) if panda else alt.NamedData.from_dict(data)

## Loads data from a URL into an altair `UrlData` object.
# @param url `str` URL string
# @returns altair `UrlData` object
def data_from_url(url):
    return alt.UrlData.from_dict(url)

## Loads data from an array (list) into an altair `InlineData` object.
# @param array `list` data values
# @returns altair `InlineData` object
def data_from_array(array):
    return alt.InlineData(array)

## Constructs an Altair graph from user data optionally saving it to an HTML file.
# @param data `DataFrame`|`NamedData` source data
# @param mark_type `str` graph mark type, any of:
# 'area', 'bar', 'circle', 'geoshape', 'image', 'line', 'point', 'rect', 'rule', 
# 'square', 'text', 'tick', 'boxplot', 'errorband', 'errorbar'
# @param mark_props `dict` property dictionary for the marks
# @param x_title `str` label for the horizontal axis
# @param x_props `dict` property dictionary for the horizontal axis
# @param y_title `str` label for the vertical axis
# @param y_props `dict` property dictionary for the vertical axis
# @param color `str`|`dict` graph color settings
# @param shape `str`|`dict` graph shape settings
# @param text_col `str` text labels for the marks
# @param text_props `dict` proprties of the text labels
# @param other_axes_and_channels `dict` additional axes / channels
# @param interactive `bool` whether the chart is interactive or static
# @param scale_factor `float` scale (zoom) factor for graph
# @param svg `bool` whether to use the SVG (vector image) renderer
# @param save_file `str` path to output file (HTML)
# @param on_save `callable` callback function called when the chart
# has been saved to the file; takes one argument -- the output file path
def make_chart(data, mark_type='point', mark_props={}, 
               x_title='x', x_props={}, 
               y_title='y', y_props={},
               color='x:N', shape='x:N',
               text_col=None, text_props={},
               other_axes_and_channels={}, interactive=True,
               scale_factor=1.0, svg=False,
               save_file='chart.html', on_save=None):

    chart = getattr(alt.Chart(data), f"mark_{mark_type}")(**mark_props)

    if 'scale' in x_props:
        x_props['scale'] = alt.Scale(domain=x_props['scale'])
    if 'scale' in y_props:
        y_props['scale'] = alt.Scale(domain=y_props['scale'])

    chart = chart.encode(
        x=alt.X(x_title, **x_props) if x_title else None,
        y=alt.Y(y_title, **y_props) if y_title else None,
        color=color if isinstance(color, str) else alt.Color(**color), 
        shape=shape if isinstance(shape, str) else alt.Shape(**shape), 
        **other_axes_and_channels)

    if text_col:
        text_chart = chart.mark_text(**text_props).encode(text=text_col)
        chart = (chart + text_chart)
        chart.properties(height=900)

    if interactive:
        chart = chart.interactive()

    if save_file:
        if svg:
            chart.save(save_file, scale_factor=scale_factor, embed_options={'renderer':'svg'})
        else:
            chart.save(save_file, scale_factor=scale_factor)
        if on_save: on_save(save_file)
# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Iskander Shafikov <s00mbre@gmail.com>
# GNU General Public License v3.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

## @package utils.graphs
import pandas as pd
import altair as alt

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def data_from_dict(data, panda=True, xy=True):
    if xy: data = {'x': list(data.keys()), 'y': list(data.values())}        
    return pd.DataFrame(data=data) if panda else alt.NamedData.from_dict(data)

def data_from_url(url):
    return alt.UrlData.from_dict(url)

def data_from_array(array):
    return alt.InlineData(array)

def make_chart(data, mark_type='point', mark_props={}, 
               x_title='x', x_props={}, 
               y_title='y', y_props={},
               color='x:N', shape='x:N',
               text_col=None, text_props={},
               other_axes_and_channels={}, interactive=True,
               scale_factor=1.0, svg=False,
               save_file='chart.html', on_save=None):
    """
    Constructs an Altair graph from data given by 'data'.

        - mark_type [str]: Any of:
            [area, bar, circle, geoshape, image, line, point, rect, rule, 
            square, text, tick, boxplot, errorband, errorbar]
    """
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
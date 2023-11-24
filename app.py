import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.figure_factory as ff
import streamlit as st
from shapely.geometry import Point
from collections import Counter


st.set_page_config(layout="wide", page_title='長目　エリアマーケティング')

# Setting Data Path:

data_dict = {
    "国勢調査": "data/kyoto_kokuse_1km.gpkg",
    "人口推計": "data/kyoto_city_1km_suikei.gpkg",
    "地価評価": "data/kyoto_chika_202307.gpkg",
}

iryo_kikan = "data/kyoto_iryo_kikan.gpkg"


# Functions


@st.cache_data
def load_data(data_path: str):
    """
    データの読み込み
    """
    df = gpd.read_file(data_path)
    return df


def sel_cols(data_name: str, df: pd.DataFrame) -> list[str]:
    """
    グラフの表示データのセレクター要素（options）の選択
    """
    if data_name == "国勢調査":
        return df.columns[1:-1]
    else:
        return df.columns[:-1]


def make_fig(
    _df: gpd.GeoDataFrame,
    _df2: gpd.GeoDataFrame,
    selected_col: str,
    n_hex: int,
    iryo: bool,
    area_set: bool,
    _df3: gpd.GeoDataFrame = None,
    lon_fl: float = None,
    lat_fl: float = None
    ):
    """
    グラフ作成用関数
    _df: 
        主となるタイルのデータ
    _df2:
        医療機関のデータ
    
    """
    _df["centroid_lat"] = _df["geometry"].map(lambda x: x.centroid.y)
    _df["centroid_lon"] = _df["geometry"].map(lambda x: x.centroid.x)
    fig = ff.create_hexbin_mapbox(
        data_frame=_df,
        lat="centroid_lat",
        lon="centroid_lon",
        nx_hexagon=n_hex,
        opacity=0.4,
        color=selected_col,
        agg_func=np.mean,
        mapbox_style="open-street-map",
        color_continuous_scale="Viridis",
        width=900,
        height=800,
    )
    fig.update_layout(mapbox=dict(pitch=50))
    if iryo:
        fig.add_scattermapbox(
            lat=_df2.geometry.y,
            lon=_df2.geometry.x,
            hovertext=_df2['P04_002'],
            marker={"color": "green", "opacity": 0.8},
        )
    if area_set:
        fig.add_scattermapbox(
            lat=[lat_fl],
            lon=[lon_fl],
            marker={'color': 'blue', 'size': 30}
        )
        poly_geo = _df3.loc[1, 'geometry']
        lons, lats = poly_geo.exterior.coords.xy
        lons = list(lons)
        lats = list(lats)
        fig.add_scattermapbox(
            mode='lines',
            lon=lons,
            lat=lats,
            line={'width': 5}
        )
    return fig

def add_market_size(gdf: gpd.GeoDataFrame, change_crs: str, market_size: int) -> gpd.GeoDataFrame:
    '''
    market_sizeで指定された円のデータをgdfに加える関数
    '''
    gdf = gdf.to_crs(change_crs)
    buff = gdf.loc[0, 'geometry'].buffer(market_size).minimum_rotated_rectangle
    gdf.loc[1, 'geometry'] = buff
    gdf = gdf.to_crs('EPSG:4326')
    return gdf


def market_data(_base_df: gpd.GeoDataFrame, _sel_df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    '''
    market内にあるデータを抽出する関数
    '''
    market_circle = _sel_df.loc[1, 'geometry']
    sel_index = _base_df.sindex.intersection(market_circle.bounds)
    _market_df = _base_df.iloc[sel_index, :-1]
    return _market_df


def iryo_market_data(_iryo_df: gpd.GeoDataFrame, _sel_df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    df = market_data(_iryo_df, _sel_df)
    return df


# Views

# sidebar view
with st.sidebar:
    option = st.selectbox(label="データ源選択", options=list(data_dict.keys()))
    data_path = data_dict[option]
    data_load_state = st.text("データをロードしています…")
    df = load_data(data_path)
    iryo_df = load_data(iryo_kikan)
    data_load_state.text("データのロードが完了しました")
    n_hex = st.slider(label="地域区分け数", min_value=3, max_value=100, value=20)
    sel_ops = sel_cols(option, df)
    select_col = st.selectbox(label="表示データ選択", options=sel_ops)
    iryo = st.checkbox("医療機関データ")
    # 商圏選択の実装
    area_set = st.checkbox("エリア指定")
    if area_set:
        lon_fl = st.slider(label='経度選択', min_value=135.570, max_value=135.870, step=0.001, value=135.760)
        lat_fl = st.slider(label='緯度選択', min_value=34.89, max_value=35.2, step=0.01, value=35.0)
        market_size = st.slider(label='エリアサイズ（m）', min_value=500, max_value=5000, step=1, value=1000)
        select_point = Point(lon_fl, lat_fl)
        sel_gdf = gpd.GeoDataFrame(geometry=[select_point], crs='EPSG:4326')
        sel_gdf = add_market_size(sel_gdf, 'EPSG:6674', market_size)
        market_df = market_data(df, sel_gdf)
        if iryo:
            iryo_market_df = iryo_market_data(iryo_df, sel_gdf)
            iryo1 = iryo_market_df['P04_004'].values
            iryo1 = [item for i2 in iryo1 for item in i2.split('　')]
            picked_iryo = pd.DataFrame(Counter(iryo1).items(), columns=['name', 'count']).sort_values('count', ascending=False).reset_index(drop=True)
    st.divider()
    st.link_button('長目をXでフォローする', 'https://twitter.com/hijichomoku')


# site main view
st.header("長目: みちび　デモサイト")
st.subheader("（データ: 京都市のみ）")

col1, col2 = st.columns((3,1))
with col2:
    torisetsu_toggle = st.toggle('使い方を見る', value=False)

if torisetsu_toggle:
    st.header('みちび: 使い方 :sunglasses:', divider='rainbow')
    st.markdown('''
        みちびはその地域の情報を提供するツールです。    
        このデモサイトでは京都市のデータのみとなっていますが、ご希望により地域、    
        ここで表示できるデータ以外のデータも扱えます。    
        各機能の使い方はチェックボックスをチェックすると確認できます！:sunglasses:     
        **お問い合わせは、[長目のフォームよりどうぞ！](https://www.chomoku.info/contact)。**    
    ''')

    st.divider()

    data_sources = st.checkbox('**データの変更方法**')
    if data_sources:
        st.markdown('''
            みちびのデモでは次の情報が得られます。    
            
            - 地域の住民数（国勢調査）
            - 地域の住民数推計値（人口推計）
            - 地域の地価（地価評価）
            
            これらは左にある「データ源選択」から選べます。    
            それぞれのデータは複数のデータを持っています。それらは「表示データ選択」で選べます。
        ''')

        st.image('img/michibi-sidebar.png')
    st.divider()

    iryo_sources = st.checkbox('**医療機関データの表示**')
    if iryo_sources:
        st.markdown('''
        みちびでは、個別の店舗などのデータも取得できます。    
        デモでは医療機関のデータを見ることが出来ます。    
        医療機関のデータを地図に載せる場合は、左の医療機関データのチェックボックスをチェックしてください。
        チェックすると、地図上に医療機関を表す緑の点が表示されます。
        ''')

        st.markdown('医療機関データをチェックすると、')
        st.image('img/michibi-iryo-on.png')
        st.markdown('地図上に医療機関のデータが表示される')
        st.image('img/michibi-iryo-map.png')
    st.divider()

    area_check_box = st.checkbox('**エリア指定の使い方**')
    if area_check_box:
        st.markdown('''
        みちびでは、位置を指定して周辺データを取得できます。    
        左のエリア指定のチェックボックスをチェックすると地図上に、中心点を示す青い丸と、
        観測エリアを示す赤い四角が表示されます。   
        地図の下には指定したエリアのデータが表示されます。
        ''')

        st.markdown('**エリア指定をチェックすると**')
        st.image('img/michibi-area-on.png')
        st.markdown('**地図上に丸と四角が表示される**')
        st.image('img/michibi-area-on-map.png')
        st.markdown('**地図の下には指定エリアの情報を表示**')
        st.image('img/michibi-area-on-df.png')

        st.markdown('''
        みちびでは、指定のエリア範囲を変更することも容易です。    
        このアプリでは経度緯度をスライダーで動かすことにより、指定のエリアを変更できます（実際は住所での指定が可能ですが、デモでは経度緯度のみの指定としています）。
        範囲もエリアサイズのスライダーを動かすことで変更できます。
        ''')

        st.markdown('**各スライダーを動かすことで地域の指定範囲を変更できる**')
        st.image('img/michibi-area-change.png')
        st.markdown('**選択範囲が更新される**')
        st.image('img/michibi-area-change-map.png')
    st.divider()

# graph
if area_set:
    fig = make_fig(df, iryo_df, select_col, n_hex, iryo, area_set, sel_gdf, lon_fl, lat_fl)
else:
    fig = make_fig(df, iryo_df, select_col, n_hex, iryo, area_set)
st.plotly_chart(fig)

if area_set:
    col1, col2 = st.columns(2)

    col1.write('エリア指定と重複するデータ')
    col1.write(market_df)

    if iryo:

        col2.write('重複する医療機関の専門')
        col2.write(picked_iryo.head(10))


if st.checkbox("データ出典: "):
    st.write(
        "人口推計、地価評価、医療機関: [国土数値情報（国交省）](https://nlftp.mlit.go.jp/)を基に[合同会社長目](https://chomoku.info)が作成"
    )
    st.write(
        "国勢調査: [e-Stat](https://www.e-stat.go.jp/gis)を基に[合同会社長目](https://chomoku.info)が作成"
    )

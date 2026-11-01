# -*- coding: utf-8 -*-
"""第三章 动态图表 第7张：动态滑珠图
源: 第三章 动态图表.xlsm / 「7 动态滑珠图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch3__7_动态滑珠图__chart1.png
实现: ECharts 交互 HTML（月份/区域单选+下拉联动滑珠值），离线单文件输出 7_动态滑珠图.html
运行: python -X utf8 7_动态滑珠图.py
"""

import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
with io.open(os.path.join(HERE, "echarts.min.js"), encoding="utf-8") as f:
    ECHARTS_JS = f.read()
OUTDIR = HERE

CSS = """
  html,body{margin:0;padding:0;background:#1A1E43;}
  #page{position:relative;background:#1A1E43;
        font-family:"Microsoft YaHei","SimHei",sans-serif;overflow:hidden;}
  #chart{position:absolute;left:0;top:0;}
  .ttl{position:absolute;color:#FFFFFF;z-index:8;white-space:nowrap;line-height:1;}
  .foot{position:absolute;color:#D9D9D9;font-size:16px;z-index:8;
        white-space:nowrap;line-height:1;}
  .ctl{position:absolute;z-index:9;font-size:16px;color:#FFFFFF;
       display:flex;align-items:center;gap:8px;white-space:nowrap;}
  .sel{background:#2C3560;color:#FFFFFF;border:1px solid #0070C0;
       font-size:16px;font-family:inherit;padding:3px 6px;outline:none;
       cursor:pointer;}
  .rdo{display:inline-flex;align-items:center;gap:4px;cursor:pointer;}
  .rdo input{accent-color:#0070C0;cursor:pointer;}
  .chk{display:inline-flex;align-items:center;gap:5px;cursor:pointer;
       font-size:16px;color:#FFFFFF;}
  .chk input{accent-color:#0070C0;cursor:pointer;}
  .btn{background:#2C3560;color:#FFFFFF;border:1px solid #5B6398;
       font-family:inherit;padding:4px 12px;font-size:14px;
       border-radius:3px;cursor:pointer;}
  .btn.on{background:#0070C0;border-color:#5EB8F5;}
"""

HTML_HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div id="page" style="width:{w}px;height:{h}px;">
  <div id="chart" style="width:{w}px;height:{h}px;"></div>
{body}
</div>
<script>
{echarts}
</script>
<script>
{js}
</script>
</body>
</html>
"""


def build(name, w, h, body, js, title=None):
    html = HTML_HEAD.format(
        title=title or name, css=CSS, w=w, h=h, body=body,
        echarts=ECHARTS_JS, js=js)
    out = os.path.join(OUTDIR, name + ".html")
    os.makedirs(OUTDIR, exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("saved:", out, os.path.getsize(out))


# ---------------- 7 动态滑珠图 ----------------
def build7():
    w, h = 844, 620
    body = """  <div class="ttl" style="left:30px;top:14px;font-size:36px;
       font-weight:bold;">2022年上半年区域销量目标达成率情况</div>
  <div class="ctl" style="right:24px;top:74px;gap:14px;">
    <label class="rdo"><input type="radio" name="mode" value="月份" checked>月份</label>
    <label class="rdo"><input type="radio" name="mode" value="区域">区域</label>
    <select id="sel" class="sel"></select>
  </div>
  <div class="foot" style="left:25px;top:580px;">*注：数据来源于公司销售系统,日期截至2022.06.30</div>
"""
    js = """
var REGIONS = ["华北","华南","东北","西北","西南","华东"];
var MONTHS = ["1月","2月","3月","4月","5月","6月"];
var M = [
  [0.32,0.45,0.66,0.52,0.69,0.771],
  [0.49,0.36,0.54,0.39,0.415,0.403],
  [0.65,0.53,0.58,0.48,0.445,0.399],
  [0.73,0.63,0.61,0.53,0.47,0.408],
  [0.536,0.498,0.527,0.708,0.7035,0.758],
  [0.32,0.49,0.65,0.73,0.536,0.7468]
];
var GRID_T = 151, BAND = (620-33-151)/6, X0 = 136, TW = 476;
var mode = "月份", chart = echarts.init(document.getElementById("chart"));

function labels(){
  if (mode === "月份") return REGIONS.slice();
  return MONTHS.slice();
}
function values(){
  var out = [];
  if (mode === "月份"){
    var mi = MONTHS.indexOf(sel.value);
    for (var i=0;i<6;i++) out.push(M[i][mi]);
  } else {
    var ri = REGIONS.indexOf(sel.value);
    for (var j=0;j<6;j++) out.push(M[ri][j]);
  }
  return out;
}
function fillSel(){
  var arr = (mode === "月份") ? MONTHS : REGIONS;
  sel.innerHTML = "";
  arr.forEach(function(t){
    var o = document.createElement("option");
    o.textContent = t; sel.appendChild(o);
  });
}
function render(){
  var vals = values();
  var rows = [];
  for (var i=0;i<6;i++) rows.push(vals[i]);
  chart.setOption({
    animationDurationUpdate:500,
    grid:{left:136, right:232, top:GRID_T, bottom:33},
    xAxis:{type:"value", min:0, max:1, show:false},
    yAxis:{type:"category", data:labels(), inverse:true,
           axisLine:{show:false}, axisTick:{show:false},
           axisLabel:{color:"#FFFFFF", fontSize:18, margin:16,
                      fontFamily:"Microsoft YaHei"}},
    series:[
      {type:"custom", renderItem:function(params, api){
        var i = params.dataIndex;
        var yc = GRID_T + BAND*(i+0.5);
        var xe = X0 + TW;
        var xv = X0 + api.value(0)*TW;
        return {type:"group", children:[
          {type:"rect", shape:{x:X0, y:yc-15, width:TW, height:30, r:15},
           style:{fill:"#7F7F7F"}},
          {type:"rect", shape:{x:X0, y:yc-15,
             width:Math.max(0, xv-X0), height:30, r:15},
           style:{fill:"#0070C0"}}
        ]};
      }, data:rows},
      {type:"scatter", data:rows.map(function(v,i){return [v,i];}),
       symbolSize:28,
       itemStyle:{color:"#0070C0", borderColor:"#FFFFFF", borderWidth:3},
       label:{show:true, position:"left", distance:6,
              color:"#FFFFFF", fontSize:18, fontFamily:"Microsoft YaHei",
              formatter:function(p){return Math.round(p.value*100)+"%";}}
      }
    ]
  }, true);
}
var sel = document.getElementById("sel");
fillSel();
render();
sel.addEventListener("change", render);
Array.prototype.forEach.call(
  document.querySelectorAll("input[name=mode]"), function(r){
  r.addEventListener("change", function(e){
    if (e.target.checked){ mode = e.target.value; fillSel(); render(); }
  });
});
"""
    build("7_动态滑珠图", w, h, body, js)


build7()

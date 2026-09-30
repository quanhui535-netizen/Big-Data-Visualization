# -*- coding: utf-8 -*-
"""第三章 动态图表 第6张：VBA动态玉玦图
源: 第三章 动态图表.xlsm / 「6 VBA动态玉玦图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch3__6_VBA动态玉玦图__chart1.png
实现: ECharts 交互 HTML（近30天/近7天按钮切换玉玦环），离线单文件输出 6_VBA动态玉玦图.html
运行: python -X utf8 6_VBA动态玉玦图.py
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


# ---------------- 6 VBA动态玉玦图 ----------------
def build6():
    w, h = 834, 594
    body = """  <div class="ttl" style="left:192px;top:21px;font-size:36px;
       font-weight:bold;">流量来源分布</div>
  <div class="ctl" style="left:596px;top:27px;gap:14px;">
    <button class="btn on" id="b30">近30天</button>
    <button class="btn" id="b7">近7天</button>
  </div>
  <div class="foot" style="left:34px;top:534px;">*注：数据来源公司网站</div>
  <div class="ttl" style="left:336.5px;width:160px;text-align:center;
       top:300.5px;font-size:16px;">首页推荐</div>
  <div class="ttl" style="left:336.5px;width:160px;text-align:center;
       top:322.5px;font-size:16px;">关注页面</div>
  <div class="ttl" style="left:336.5px;width:160px;text-align:center;
       top:344.5px;font-size:16px;">搜索</div>
  <div class="ttl" style="left:336.5px;width:160px;text-align:center;
       top:366.5px;font-size:16px;">个人主页</div>
"""
    js = """
var NAMES = ["个人主页","搜索","关注页面","首页推荐"];
var COLORS = ["#00B0F0","#11A7AD","#FFC000","#E74E69"];
var DATA = {"近30天":[0.09,0.24,0.29,0.38], "近7天":[0.13,0.19,0.32,0.36]};
var cur = "近30天";
var chart = echarts.init(document.getElementById("chart"));
function render(){
  var vals = DATA[cur], out = [];
  var rIn = 181*0.35, slot = (181-181*0.35)/4;
  for (var i=0;i<4;i++){
    out.push({
      type:"pie", center:[420.5,345.5],
      radius:[rIn+i*slot, rIn+(i+1)*slot],
      startAngle:90, z:i+1,
      label:{show:false}, labelLine:{show:false},
      data:[
        {value:vals[i], itemStyle:{color:COLORS[i],
         borderColor:"#1A1E43", borderWidth:1.2}},
        {value:0.5-vals[i], itemStyle:{color:"transparent",
         borderColor:"transparent"}}
      ]
    });
  }
  chart.setOption({animationDurationUpdate:600, series:out}, true);
}
render();
function bind(id, val, btns){
  document.getElementById(id).addEventListener("click", function(){
    cur = val;
    btns.forEach(function(b){
      document.getElementById(b).classList.toggle("on",
        document.getElementById(b).id === id);
    });
    render();
  });
}
bind("b30","近30天",["b30","b7"]);
bind("b7","近7天",["b30","b7"]);
"""
    build("6_VBA动态玉玦图", w, h, body, js)


build6()

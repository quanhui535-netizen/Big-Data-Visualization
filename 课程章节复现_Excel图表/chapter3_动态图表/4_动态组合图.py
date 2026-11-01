# -*- coding: utf-8 -*-
"""第三章 动态图表 第4张：动态组合图
源: 第三章 动态图表.xlsm / 「4 动态组合图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch3__4_动态组合图__chart1.png
实现: ECharts 交互 HTML（销售额/利润额/利润率复选框显隐系列），离线单文件输出 4_动态组合图.html
运行: python -X utf8 4_动态组合图.py
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


# ---------------- 4 动态组合图 ----------------
def build4():
    w, h = 828, 592
    body = """  <div class="ttl" style="left:67px;top:43px;font-size:36px;
       font-weight:bold;">2022年化妆品销售情况</div>
  <div class="ctl" style="left:520px;top:46px;gap:14px;">
    <label class="chk"><input type="checkbox" id="cSales" checked>销售额</label>
    <label class="chk"><input type="checkbox" id="cProfit" checked>利润额</label>
    <label class="chk"><input type="checkbox" id="cRate" checked>利润率</label>
  </div>
  <div class="foot" style="left:57px;top:555px;">*注：数据来源公司销售系统</div>
"""
    js = """
var CATS = ["口红","面膜","隔离","粉底液"];
var SALES = [2800,2564,2282,2353];
var PROFIT = [1896,1563,986,1324];
var RATE = [0.6771428571428572,0.609594383775351,
            0.43207712532865905,0.5626859328516787];
var chart = echarts.init(document.getElementById("chart"));
function base(){
  return {
    animationDurationUpdate:500,
    grid:{left:36, right:42, top:192, bottom:102.5},
    tooltip:{trigger:"axis", backgroundColor:"#2C3560",
             borderColor:"#0070C0",
             textStyle:{color:"#FFFFFF", fontFamily:"Microsoft YaHei"}},
    xAxis:{type:"category", data:CATS, boundaryGap:true,
           axisLine:{show:true, lineStyle:{color:"#2A2E4F", width:1.2}},
           axisTick:{show:false},
           axisLabel:{color:"#FFFFFF", fontSize:18, margin:15,
                      fontFamily:"Microsoft YaHei"}},
    yAxis:[
      {type:"value", min:0, max:3500, show:false},
      {type:"value", min:-1.0172, max:0.7391, show:false}
    ],
    series:[]
  };
}
function seriesOpt(){
  var s = [];
  s.push({
    name:"销售额", type:"bar", data:SALES, barWidth:42, barGap:"26%",
    itemStyle:{color:"#0070C0"},
    label:{show:true, color:"#FFFFFF", fontSize:18, position:"insideTop",
           distance:5, fontFamily:"Microsoft YaHei",
           formatter:function(p){return p.value;}},
    emphasis:{focus:"series"}
  });
  s.push({
    name:"利润额", type:"bar", data:PROFIT, barWidth:42,
    itemStyle:{color:"#E74E69"},
    label:{show:true, color:"#FFFFFF", fontSize:18, position:"insideTop",
           distance:5, fontFamily:"Microsoft YaHei",
           formatter:function(p){return p.value;}},
    emphasis:{focus:"series"}
  });
  s.push({
    name:"利润率", type:"line", yAxisIndex:1, data:RATE,
    symbol:"circle", symbolSize:1, lineStyle:{color:"#FFC000", width:2.2},
    itemStyle:{color:"#FFC000"},
    label:{show:true, color:"#FFFFFF", fontSize:18, position:"top",
           distance:12, fontFamily:"Microsoft YaHei",
           formatter:function(p){return Math.round(p.value*100)+"%";}},
    emphasis:{focus:"series"}
  });
  return s;
}
function render(){
  var opt = base();
  var show = [cSales.checked, cProfit.checked, cRate.checked];
  var ss = seriesOpt();
  for (var i=0;i<3;i++){
    if (show[i]) opt.series.push(ss[i]);
    else opt.series.push({name:ss[i].name, type:ss[i].type, data:[],
                          yAxisIndex:ss[i].yAxisIndex||0});
  }
  chart.setOption(opt, true);
}
["cSales","cProfit","cRate"].forEach(function(id){
  document.getElementById(id).addEventListener("change", render);
});
render();
"""
    build("4_动态组合图", w, h, body, js)


build4()

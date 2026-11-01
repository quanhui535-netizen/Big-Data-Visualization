# -*- coding: utf-8 -*-
"""第三章 动态图表 第1张：动态柱形图
源: 第三章 动态图表.xlsm / 「1 动态柱形图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch3__1_动态柱形图__chart1.png
实现: ECharts 交互 HTML（月份下拉切换1~6月数据，y轴自适应），离线单文件输出 1_动态柱形图.html
运行: python -X utf8 1_动态柱形图.py
"""
import io
import os

ECH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "echarts.min.js")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "1_动态柱形图.html")

with io.open(ECH, encoding="utf-8") as f:
    echarts_js = f.read()

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>1_动态柱形图</title>
<style>
  html,body{margin:0;padding:0;background:#1A1E43;}
  #page{position:relative;width:732px;height:535px;background:#1A1E43;
        font-family:"Microsoft YaHei","SimHei",sans-serif;overflow:hidden;}
  #chart{position:absolute;left:0;top:0;width:732px;height:535px;}
  #title{position:absolute;left:56px;top:36px;color:#FFFFFF;font-size:36px;
         font-weight:bold;z-index:8;white-space:nowrap;}
  #foot{position:absolute;left:56px;top:497px;color:#D9D9D9;font-size:16px;
        z-index:8;white-space:nowrap;}
  #ctrl{position:absolute;right:36px;top:40px;z-index:9;font-size:16px;
        color:#FFFFFF;display:flex;align-items:center;gap:8px;}
  #month{background:#2C3560;color:#FFFFFF;border:1px solid #0070C0;
         font-size:16px;font-family:inherit;padding:4px 8px;outline:none;
         cursor:pointer;}
</style>
</head>
<body>
<div id="page">
  <div id="chart"></div>
  <div id="title">2022年上半年各区域销售情况</div>
  <div id="ctrl">月份
    <select id="month">
      <option>1月</option><option>2月</option><option>3月</option>
      <option>4月</option><option selected>5月</option><option>6月</option>
    </select>
  </div>
  <div id="foot">*注：数据来源公司销售系统</div>
</div>
<script>
__ECHARTS__
</script>
<script>
var CATS = ["华北","华南","东北","西北","西南","华东"];
var DATA = {
  "1月":[259,247,705,513,463,384],
  "2月":[235,266,529,324,579,282],
  "3月":[330,342,705,540,492,308],
  "4月":[282,342,599,270,492,384],
  "5月":[282,323,705,486,405,308],
  "6月":[965,380,282,567,463,897]
};
var chart = echarts.init(document.getElementById("chart"), null, {renderer:"canvas"});
function axisMax(vals){
  var m = Math.max.apply(null, vals);
  return Math.max(800, Math.ceil(m/200)*200);
}
function build(month){
  var vals = DATA[month];
  return {
    animationDurationUpdate: 500,
    grid: {left:95, right:46, top:149, bottom:96},
    tooltip: {
      trigger:"axis",
      backgroundColor:"#2C3560", borderColor:"#0070C0",
      textStyle:{color:"#FFFFFF", fontFamily:"Microsoft YaHei"}
    },
    xAxis: {
      type:"category", data:CATS, boundaryGap:true,
      axisLine:{show:false}, axisTick:{show:false},
      axisLabel:{color:"#FFFFFF", fontSize:16, margin:15,
                 fontFamily:"Microsoft YaHei"}
    },
    yAxis: {
      type:"value", min:0, max:axisMax(vals), interval:200,
      axisLine:{show:false}, axisTick:{show:false},
      axisLabel:{color:"#FFFFFF", fontSize:16, fontFamily:"Microsoft YaHei"},
      splitLine:{show:true, lineStyle:{color:"#434664", width:1, type:[12,6]}}
    },
    series: [{
      type:"bar", data:vals, barWidth:39,
      itemStyle:{color:"#0097E0"}
    }]
  };
}
chart.setOption(build("5月"));
document.getElementById("month").addEventListener("change", function(e){
  chart.setOption(build(e.target.value), true);
});
window.addEventListener("resize", function(){ chart.resize(); });
</script>
</body>
</html>
"""

html = html.replace("__ECHARTS__", echarts_js)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("saved:", OUT, os.path.getsize(OUT))

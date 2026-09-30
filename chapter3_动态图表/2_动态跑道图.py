# -*- coding: utf-8 -*-
"""第三章 动态图表 第2张：动态跑道图
源: 第三章 动态图表.xlsm / 「2 动态跑道图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch3__2_动态跑道图__chart1.png
实现: ECharts 交互 HTML（月份下拉切换1~4月，标题/环带/部门标签联动），离线单文件输出 2_动态跑道图.html
运行: python -X utf8 2_动态跑道图.py
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


# ---------------- 2 动态跑道图 ----------------
def build2():
    w, h = 832, 622
    body = """  <div id="ttl" class="ttl" style="left:0;width:{W}px;top:40px;
       font-size:24px;text-align:center;">4月公司总人数为1637</div>
  <div class="ctl" style="left:718px;top:47px;">
    <select id="month" class="sel">
      <option>1月</option><option>2月</option><option>3月</option>
      <option selected>4月</option>
    </select>
  </div>
  <div class="foot" style="left:40px;top:552px;">*注：数据来源公司人力资源系统</div>
""".replace("{W}", str(w))
    js = """
var DEPTS = ["人力部","行政部","财务部","工程部","采购部","销售部"];
var LABS  = ["销售部","采购部","工程部","财务部","行政部","人力部"];
var COLORS = ["#7030A0","#0070C0","#37A2DA","#11A7AD","#F5C353","#E74E69"];
var MONTHS = {
  "1月":[130,226,238,293,326,451], "2月":[138,206,228,305,349,456],
  "3月":[130,217,255,314,316,406], "4月":[129,226,226,264,359,433]
};
var SUMS = {"1月":1664,"2月":1682,"3月":1638,"4月":1637};
var IDX  = [5,4,3,2,1,0];
var chart = echarts.init(document.getElementById("chart"));
var labDivs = [];
(function(){
  var page = document.getElementById("page");
  for (var i=0;i<6;i++){
    var d = document.createElement("div");
    d.className = "ttl";
    d.style.cssText = "left:0;width:334px;top:"+(175+i*22-9)+"px;"
      + "font-size:12px;text-align:right;";
    page.appendChild(d);
    labDivs.push(d);
  }
})();
function series(vals){
  var sum2 = SUMS[curM]/2, out = [];
  for (var i=0;i<6;i++){
    out.push({
      type:"pie", center:[374.2,356.85], radius:[RIN+i*SLOT, RIN+(i+1)*SLOT],
      startAngle:90, silent:false, z:i+1,
      label:{show:false}, labelLine:{show:false},
      data:[
        {value:vals[i], itemStyle:{color:COLORS[i],
         borderColor:"#1A1E43", borderWidth:1.5}},
        {value:sum2-vals[i], itemStyle:{color:"transparent",
         borderColor:"transparent"}}
      ]
    });
  }
  return out;
}
var RIN = 201.5*0.45, SLOT = (201.5-201.5*0.45)/6, curM = "4月";
function render(){
  var vals = MONTHS[curM];
  document.getElementById("ttl").textContent =
    curM + "公司总人数为" + SUMS[curM];
  for (var i=0;i<6;i++)
    labDivs[i].textContent = LABS[i] + " " + vals[IDX[i]];
  chart.setOption({animationDurationUpdate:600, series:series(vals)}, true);
}
render();
document.getElementById("month").addEventListener("change", function(e){
  curM = e.target.value; render();
});
"""
    build("2_动态跑道图", w, h, body, js)


build2()

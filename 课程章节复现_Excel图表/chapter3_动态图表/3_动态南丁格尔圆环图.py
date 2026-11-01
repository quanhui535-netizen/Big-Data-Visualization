# -*- coding: utf-8 -*-
"""第三章 动态图表 第3张：动态南丁格尔圆环图
源: 第三章 动态图表.xlsm / 「3 动态南丁格尔圆环图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch3__3_动态南丁格尔圆环图__chart1.png
实现: ECharts 交互 HTML（近7天/近30天单选切换扇区与百分比），离线单文件输出 3_动态南丁格尔圆环图.html
运行: python -X utf8 3_动态南丁格尔圆环图.py
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


# ---------------- 3 动态南丁格尔圆环图 ----------------
def build3():
    w, h = 830, 590
    body = """  <div class="ttl" style="left:42px;top:25px;font-size:36px;
       font-weight:bold;">2022年6月30日流量来源分布</div>
  <div class="ctl" style="left:664px;top:66px;gap:12px;">
    <label class="rdo"><input type="radio" name="pd" value="近7天" checked>近7天</label>
    <label class="rdo"><input type="radio" name="pd" value="近30天">近30天</label>
  </div>
  <div class="foot" style="left:32px;top:526px;">*注：数据来源公司网站</div>
"""
    js = """
var NAMES = ["首页推荐","关注页面","搜索","个人主页","其他来源"];
var DATA = {
  "近7天":  [0.44,0.17,0.15,0.08,0.16],
  "近30天": [0.38,0.21,0.15,0.09,0.17]
};
var FILLS = ["#4A5BD1","#FFC000","#E66B4C","#6073F3","#11A7AD"];
var PCOL  = ["#6073F3","#FFC000","#E66B4C","#6073F3","#11A7AD"];
var POS = [[680,250],[175,330],[210,215],[545,520],[230,470]];
var chart = echarts.init(document.getElementById("chart"));
var nameDivs = [], pctDivs = [];
(function(){
  var page = document.getElementById("page");
  for (var i=0;i<5;i++){
    var n = document.createElement("div");
    n.className = "ttl";
    n.style.cssText = "left:"+(POS[i][0]-70)+"px;width:140px;text-align:center;"
      + "top:"+(POS[i][1]-25)+"px;font-size:18px;";
    page.appendChild(n); nameDivs.push(n);
    var p = document.createElement("div");
    p.className = "ttl";
    p.style.cssText = "left:"+(POS[i][0]-70)+"px;width:140px;text-align:center;"
      + "top:"+(POS[i][1]+5)+"px;font-size:18px;color:"+PCOL[i]+";";
    page.appendChild(p); pctDivs.push(p);
  }
})();
function render(){
  var vals = DATA[curP];
  for (var i=0;i<5;i++){
    nameDivs[i].textContent = NAMES[i];
    pctDivs[i].textContent = Math.round(vals[i]*100) + "%";
  }
  chart.setOption({
    animationDurationUpdate:600,
    series:[{
      type:"pie", center:[415,340], radius:[175*0.52,175],
      startAngle:90,
      label:{show:false}, labelLine:{show:false},
      itemStyle:{borderColor:"#1A1E43", borderWidth:1.5},
      data: vals.map(function(v,i){
        return {value:v, name:NAMES[i], itemStyle:{color:FILLS[i]}};
      })
    }]
  }, true);
}
var curP = "近7天";
render();
Array.prototype.forEach.call(
  document.querySelectorAll("input[name=pd]"), function(r){
  r.addEventListener("change", function(e){
    if (e.target.checked){ curP = e.target.value; render(); }
  });
});
"""
    build("3_动态南丁格尔圆环图", w, h, body, js)


build3()

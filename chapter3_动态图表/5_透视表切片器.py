# -*- coding: utf-8 -*-
"""第三章 动态图表 第5张：透视表切片器
源: 第三章 动态图表.xlsm / 「5 透视表切片器」
参考原图: D:\\Software\\node\\bipviz\\references\\ch3__5_透视表切片器__chart1.png
实现: ECharts 交互 HTML（7部门切片器（单击单选、Ctrl多选）重算各学历平均工资），离线单文件输出 5_透视表切片器.html
运行: python -X utf8 5_透视表切片器.py
"""

import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
with io.open(os.path.join(HERE, "echarts.min.js"), encoding="utf-8") as f:
    ECHARTS_JS = f.read()
OUTDIR = HERE

SLICER_JSON = r'''{"depts": ["销售", "行政", "人力资源", "市场拓展", "工程", "后勤", "财务"], "order": ["本科", "博士", "高中", "硕士", "专科"], "per": {"销售": {"cnt": {"专科": 87, "硕士": 128, "本科": 166, "博士": 15, "高中": 50}, "sum": {"专科": 567139.0, "硕士": 935006.0, "本科": 1187693.0, "博士": 132588.0, "高中": 281365.0}}, "行政": {"cnt": {"高中": 32, "本科": 121, "专科": 56, "硕士": 83, "博士": 13}, "sum": {"高中": 201259.0, "本科": 761899.0, "专科": 282044.0, "硕士": 472776.0, "博士": 130459.0}}, "人力资源": {"cnt": {"专科": 15, "硕士": 15, "本科": 27, "高中": 5, "博士": 3}, "sum": {"专科": 67336.0, "硕士": 145667.0, "本科": 182535.0, "高中": 13883.0, "博士": 14971.0}}, "市场拓展": {"cnt": {"硕士": 162, "本科": 230, "专科": 119, "高中": 73, "博士": 16}, "sum": {"硕士": 1091720.0, "本科": 1411813.0, "专科": 822057.0, "高中": 427315.0, "博士": 114992.0}}, "工程": {"cnt": {"高中": 1}, "sum": {"高中": 3468.0}}, "后勤": {"cnt": {"高中": 1}, "sum": {"高中": 2693.0}}, "财务": {"cnt": {"专科": 5, "本科": 28, "高中": 8, "硕士": 10, "博士": 1}, "sum": {"专科": 17338.0, "本科": 183935.0, "高中": 28914.0, "硕士": 74127.0, "博士": 4317.0}}}}'''

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


# ---------------- 5 透视表切片器 ----------------
def build5():
    w, h = 854, 578
    body = """  <div class="ttl" style="left:49px;top:56px;font-size:36px;
       font-weight:bold;">各学历平均工资情况</div>
  <div id="slicer" style="position:absolute;left:504px;top:14px;width:330px;
       background:#2C3560;border:1px solid #465081;border-radius:3px;
       z-index:9;padding:4px 6px 8px;box-sizing:border-box;">
    <div style="color:#FFFFFF;font-size:15px;padding:3px 2px 6px;">部门</div>
    <div id="slItems" style="display:grid;grid-template-columns:repeat(4,1fr);
         gap:5px;"></div>
  </div>
  <div class="foot" style="left:40px;top:537px;">*注：数据来源于人力资源管理系统，统计日期截至2022.03.31</div>
"""
    js = """
var SD = __SLICER__;
var chart = echarts.init(document.getElementById("chart"));
var sel = {"市场拓展":true};
(function(){
  var box = document.getElementById("slItems");
  SD.depts.forEach(function(dp){
    var b = document.createElement("button");
    b.className = "btn"; b.textContent = dp;
    b.style.fontSize = "14px"; b.style.padding = "3px 2px";
    b.addEventListener("click", function(e){
      if (e.ctrlKey || e.metaKey || e.shiftKey){
        if (sel[dp]){
          var cnt = SD.depts.filter(function(d){return sel[d];}).length;
          if (cnt <= 1) return;
          delete sel[dp];
        } else sel[dp] = true;
      } else {
        sel = {}; sel[dp] = true;
      }
      syncBtns(); render();
    });
    b._dp = dp;
    box.appendChild(b);
  });
  syncBtns();
})();
function syncBtns(){
  Array.prototype.forEach.call(
    document.querySelectorAll("#slItems .btn"), function(b){
    if (sel[b._dp]) b.classList.add("on");
    else b.classList.remove("on");
  });
}
function calc(){
  var out = [];
  SD.order.forEach(function(ed){
    var sc = 0, ss = 0;
    SD.depts.forEach(function(dp){
      if (sel[dp]){
        sc += (SD.per[dp].cnt[ed] || 0);
        ss += (SD.per[dp].sum[ed] || 0);
      }
    });
    out.push(sc > 0 ? ss/sc : 0);
  });
  return out;
}
function render(){
  var vals = calc();
  chart.setOption({
    animationDurationUpdate:500,
    grid:{left:56, right:61, top:151.5, bottom:103.5},
    xAxis:{type:"category", data:SD.order, boundaryGap:true,
           axisLine:{show:false}, axisTick:{show:false},
           axisLabel:{color:"#FFFFFF", fontSize:18, margin:15,
                      fontFamily:"Microsoft YaHei"}},
    yAxis:{type:"value", min:0, max:10000, interval:2500,
           axisLine:{show:false}, axisTick:{show:false},
           axisLabel:{show:false},
           splitLine:{show:true,
             lineStyle:{color:"#454866", width:1, type:[12,6]}}},
    series:[{
      type:"bar", data:vals, barWidth:46.5,
      itemStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,
        [{offset:0,color:"#0070C0"},{offset:1,color:"#00B0F0"}])},
      label:{show:true, color:"#FFFFFF", fontSize:18, position:"top",
             distance:5, fontFamily:"Microsoft YaHei",
             formatter:function(p){
               return p.value > 0 ? p.value.toFixed(2) : "";
             }}
    }]
  }, true);
}
render();
"""
    js = js.replace("__SLICER__", SLICER_JSON)
    build("5_透视表切片器", w, h, body, js)


build5()

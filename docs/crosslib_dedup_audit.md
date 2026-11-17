# 跨库基准排重审计(ECOSTRESS / RELAB vs bundled rf77)

> 脚本:`docs/_audit_crosslib_dedup.py`(可重复执行) | 数据:ECOSTRESS `/media/lee/共享14/backup/ecospeclib-all` / RELAB `/media/lee/共享14/backup/relab`

## 方法

- 打包参考:77 规则 → 68 唯一标签 = 58 物理记录 + 10 合成混合物;
  从物理记录标签提取样品登录号 token **63 个**(GDS/CU/HS/NMNH/AMX/粘土标样等,模式见脚本 TOKEN_PATTERNS)。
- token 匹配:登录号各字母数字段之间允许任意非字母数字间隔,两侧防子串误配;命中 `name`/登录号字段/文件名/标本号 记 **strong**(标本号级同源),仅命中 description 等自由文本记 **weak**(人工复核)。

## ECOSTRESS 池

| category | wrange | 记录数 |
|---|---|---|
| manmade | all | 45 |
| manmade | tir | 27 |
| meteorites | tir | 59 |
| mineral | all | 22 |
| mineral | tir | 751 |
| mineral | vswir | 836 |
| nonphotosyntheticvegetation | all | 1 |
| nonphotosyntheticvegetation | tir | 61 |
| nonphotosyntheticvegetation | vswir | 61 |
| rock | all | 381 |
| rock | tir | 6 |
| rock | vswir | 83 |
| soil | all | 41 |
| soil | tir | 28 |
| vegetation | all | 3 |
| vegetation | tir | 484 |
| vegetation | vswir | 553 |
| water | all | 6 |
| water | tir | 3 |
| **合计** | | **3451** |

- 命中记录 0 条(strong 0 条 / weak 见 CSV)。
- 基准相关池 mineral ∩ (vswir|all) = **858** 条,其中 strong 排除 **0** 条,剩余独立 **858** 条。
- 零命中复核(防脚本漏配):对打包参考中的代表样品做关键词抽查——engelmann/lodgepole/spruce 命中 0;montmor/alunite/muscovite 命中的记录全部为 JPL(`so-4a`/`ps-16a`)/JHU(`montmor_1`/`alunite_2`)内部编号,无 USGS 登录号;库内 21 条 usgs.perknic 矿物记录(gds147/nmnh##### 等)均不在打包 token 集内。**登录号级同源为零的结论成立。**残余风险:不同登录号但同矿区的样品(token 以下粒度)无法机械排除,基准成稿时按族抽看产地字段即可。

## RELAB 池

- 记录 23606 条;命中记录 450 条 / 命中对 466 组(strong 465;weak 1)。
- **关键发现**:RELAB 测量过 CMS 粘土标样(SWy-1/SWy-2/SAz-1/NG-1/KGa-2/IMt-1/SHCa-1)——与 splib07 打包参考同一材料来源(Source Clays Repository)。RELAB 腿对蒙脱石/高岭石/伊利石/绿土族**不构成独立验证**:纯标样记录须从独立池剔除(可单列为跨设施同材料一致性组);衍生/混合样(阳离子交换、比例混合)不是单矿物身份真值,按混合样另行处理。

### 同源命中汇总(按 token)

| token | bundled 参考 | 命中对 | 纯样 | 衍生/混合 | 纯样唯一样品名 |
|---|---|---|---|---|---|
| SWy-1 | Montmorillonite_SWy-1_NIC4bcc_RREF | 183 | 42 | 141 | Montmorillonite Swy-1<br>Montmorillonite Swy-1 pellet<br>Montmorillonite- SWy-1<br>Montmorillonite- SWy-1 (SK)<br>Montmorillonite- Swy-1<br>Na-Montmorillonite SWy-1- Cogoini #NM-org<br>SWy-1 monomorillonite bulk<br>SWy-1 montmorillonite<br>SWy-1 montmorillonite 125-250 um<br>SWy-1 montmorillonite 75-125 um<br>Smectite- SWy-1<br>Will Gates #12 montmorillonite Swy-1 from Wyoming |
| NG-1 | Nontronite_NG-1.b_lt2um_fr_NIC4bb_RREF | 163 | 36 | 127 | Nontronite- NG-1 |
| SWy-2 | Water+Montmor_SWy-2+0.50g-l_ASDFRa_AREF; Water+Montmor_SWy-2+5.01g-l_ASDFRa_AREF | 34 | 8 | 26 | Montmorillonite- CMS standard SWy-2<br>Montmorillonite- SWy-2 (Berlin)<br>Will Gates #13 montmorillonite Swy-2 from Wyoming |
| IMt-1 | Illite_IMt-1.b_lt2um_BECKa_AREF | 29 | 9 | 20 | Illite IMt-1 part (Clay Smectite Illite)<br>Illite IMt-1 pellet (Clay Smectite Illite)<br>Illite- CMS Standard IMt-1<br>Illite- IMt-1<br>Illite-Smectite Mixed Layer- Imt-1 |
| NG-1.b | Nontronite_NG-1.b_lt2um_fr_NIC4bb_RREF | 27 | 0 | 27 | — |
| SAz-1 | Montmorillonite_SAz-1_NIC4bb_RREF | 16 | 12 | 4 | Montmorillonite SAz-1<br>SAz-1 montmorillonite<br>Smectite- SAz-1<br>Will Gates #5 montmorillonite SAz-1 |
| KGa-2 | Kaolinite_KGa-2_(pxl)_NIC4bbb_RREF | 12 | 4 | 8 | Hydrated Clay- KGa-2<br>Kaolinite KGa-2, CMS standard |
| SHCa-1 | Hectorite_SHCa-1.Ac-B_NIC4bb_RREF | 1 | 1 | 0 | Hectorite- SHCa-1 |

> 处置:纯样 112 组(上表"纯样"列)→ 从 RELAB 独立池剔除;衍生/混合 353 组 → 混合样另案。逐条清单见 `crosslib_dedup_hits.csv`。

weak 命中 1 组(仅 description 字段),逐条见 CSV。

## 复核结论

1. **ECOSTRESS 腿(3451 条)登录号级同源 = 0**,858 条 VSWIR/all 矿物记录可入独立池(vegetation/water 章若纳入基准同样零命中)。
2. **RELAB 腿(23606 条)不独立区间 = CMS 粘土标样**:8 个 token、450 条记录(纯标样 + 同材料衍生/混合)。smectite/kaolinite/illite 族的 RELAB 命中率必须剔除这些记录后计算,或把纯标样单列"跨设施同材料一致性"对照组(双向几何 vs splib 半球几何,本身有方法学价值)。
3. weak 命中(description 字段)已随 CSV 产出,量级 1 组,无处置需求。
4. 后续基准脚本(第 2 步 RELAB 遴选)须读取本审计的排除清单:`crosslib_dedup_hits.csv` 中 strength=strong 的 spec_id 全部排除。

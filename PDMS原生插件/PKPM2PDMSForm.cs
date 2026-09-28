// PKPM2PDMSForm.cs - PKPM2PDMS import/export tool window (WinForms, non-modal singleton).
// 控件清单冻结：契约 CONTRACT.md §p.3 的 13 项表（控件名逐一对应，不得增删语义）。
// 窗体写法参照：D:\AI_Work\PDMS三维文字程序\TGTEXT\TextForm.cs
//   （13 public class TextForm : Form；:55-60 构造器 BuildUi；:74-83 FormStyle：
//   StartPosition/ShowInTaskbar=false 工具窗体；:29 控件声明分组注释风格）。
// 执行序列冻结：契约 §p.5 ①-⑤（校验 -> 写 request -> 进程等待 -> 执行宏+取回改名 -> 摘要上窗）。
// 混写红线（§p.4）：本窗体不读写 .jwd/.pdt —— 格式转换全部由引擎进程完成；
//   PDMS 库内动作（导出 PML / 执行宏 / 取回改名记录）全部经 PmlBridge。
//
// 〔R6 用户实机反馈三项修复（2026-09-28）〕
//   ① 多余窗口：点「执行」后弹出的第二个窗口（要手填文件路径与匹配文件路径）来自引擎
//      启动器的 tkinter GUI（无 --cli 即开）。修复：EngineRunner 调用带 --cli（见该文件），
//      且本窗体的"执行"路径不再弹任何窗口（失败一律落摘要区 + addin.log）。
//   ② 一键化：导入方向（auto2pdms）＝ 引擎生成宏（临时目录）→ 立即在 PDMS 内执行 →
//      结果（成功/失败、构件计数、命名结果）显示在摘要区；用户全程不接触宏文件。
//      宏本体由引擎按"DB Output 宏"标准结构生成（见 macgen.py）。
//   ③ 下拉三项（中文显示，值映射到引擎子命令）：
//      ① PKPM导入PDMS → auto2pdms（按文件内容自动识别 .jwd/.pdt）
//      ② PDMS导出PDT文件 → pdms2pdt      ③ PDMS导出JWD文件 → pdms2jwd
//
// 〔R7 改造（2026-09-28，用户确认的命名方案）〕
//   执行链（一键导入，全程除窗体自身刷新外零新窗口）：
//     ① 点「执行」→ 校验输入；
//     ② **SITE 名探测**：SiteProber（DbElement 直查逐个试名 /PKPM2PDMS → /PKPM2PDMSre → …
//        re99，静默零弹窗；直查不可用时回退 Q 命令，同样静默）试出第一个可用的顶层名；
//        全占满 / 机制不可用 ⇒ 摘要区明确报错，**不执行导入**；
//     ③ 组装 --request（新增键 site_name）+ 调引擎（--cli，带 --request）；
//     ④ 引擎生成宏（生成期名字查重 + 落盘前全量自查重；底层 SCTN/PANE/STWALL 无名创建）；
//     ⑤ 本窗体 `$M '<宏全路径>'` 执行（.mac 的 $M 合法：官方先例 = PMLLIB 的
//        common\forms\*macro*.pmlfrm:76-86 的 `$m "$!this.<成员>"`）→ 结果 + 引擎 report 的
//        命名结果（site_name / stats.used_names_count / stats.unnamed_count）写摘要区。
//   删除对 PML 唯一化函数的一切依赖：本包不再预载/调用任何 PML 辅助函数（唯一化 + 运行入口
//     整族已退役，退役清单见 deploy_pkpm2pdms.py 的 RETIRED_PML 与 ENGINE_IO.md §8），
//     宏里也不再出现任何 !!pkpm2pdms* 调用（改名责任全在 .NET 探测侧 + 引擎生成期查重）。
//     $M <文件>.pmlfnc 本机实测无效（(46,80) PML: Invalid syntax），本包从不 $M 任何 .pmlfnc；
//     $M 只用于引擎生成的 .mac。
using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Text;
using System.Threading;
using System.Windows.Forms;

namespace PKPM2PDMS
{
    public class PKPM2PDMSForm : Form
    {
        // ---- §p.3 #1：操作下拉（R6 问题③：窗体只保留三项，显示中文；值 = 引擎子命令） ----
        private ComboBox cmbOp;
        // ---- #2：源文件 ----
        private TextBox txtSource;
        private Button btnBrowseSource;
        // ---- #3：截面匹配文件 ----
        private TextBox txtSecmap;
        private Button btnBrowseSecmap;
        // ---- #4：补充映射 ----
        private CheckBox chkUseExtra;
        private TextBox txtExtra;
        // ---- #5/#6/#7：建模参数 ----
        private NumericUpDown numBaseE;
        private NumericUpDown numBaseN;
        private NumericUpDown numBaseU;
        private NumericUpDown numAngle;
        private ComboBox cmbUnit;
        // ---- #8：构件类别勾选（与现有 Add-in Chk_* 同名同义；本包拆 HBrace/VBrace） ----
        private CheckBox chkColumn, chkBeam, chkHBrace, chkVBrace;
        private CheckBox chkSlab, chkWall, chkGrid, chkHole;
        // ---- #9：输出文件 ----
        private TextBox txtOut;
        private Button btnBrowseOut;
        // ---- #10/#11/#12：执行、进度与摘要、打开报告 ----
        private Button btnRun;
        private ProgressBar progressBar1;
        private TextBox txtSummary;
        private Button btnOpenReport;

        // 运行状态（progressBar 与 worker 线程间通过 _running 标志联动）
        private volatile bool _running;
        private Thread _worker;
        private System.Windows.Forms.Timer _progTimer;   // 全限定：与 System.Threading.Timer 消歧（TGTextAddin.cs:45 同法）
        private EngineResult _result;
        private string _reportPath = "";
        private string _runError = "";
        private bool _secmapAuto = true;     // txtSecmap 是否处于"自动预填"状态
        private string _lastAutoSecmap = ""; // 最近一次自动预填的值
        private bool _outAuto = true;        // txtOut 是否处于"自动预填"状态（R6：用户改过就不再覆盖）
        private string _lastAutoOut = "";    // 最近一次自动预填的输出路径
        private string _siteName = "";       // 〔R7〕本次探测出的可用 SITE 名（导入方向；复核/摘要用）

        private const string DefaultSecmapName = "PKPM转PDMS截面匹配文件.txt";   // 契约 §f.1 同规则

        // ---- 操作项（R6 问题③：显示中文 / 值 = 引擎子命令） ----
        private sealed class OpItem
        {
            public readonly string Text;    // 窗体显示（中文）
            public readonly string Op;      // 引擎子命令（= --request 的 tool；§m.1 的名字）
            public OpItem(string text, string op) { Text = text; Op = op; }
            public override string ToString() { return Text; }   // ComboBox 靠 ToString 显示
        }

        // 三项 = 用户实机反馈收敛后的全集（其余 7 个方向只在引擎 CLI 里保留，不上窗体）：
        //   ① auto2pdms —— 导入（自动识别 .jwd/.pdt，B 包实现；原 jwd2pdms/pdt2pdms 的合一）
        //   ② pdms2pdt   —— 导出 .pdt（dump 文本来自 PML !!pkpm2pdmsexport）
        //   ③ pdms2jwd   —— 导出 .jwd（同上）
        private static readonly OpItem[] OpItems = new OpItem[] {
            new OpItem("PKPM导入PDMS",      "auto2pdms"),
            new OpItem("PDMS导出PDT文件",   "pdms2pdt"),
            new OpItem("PDMS导出JWD文件",   "pdms2jwd"),
        };

        public PKPM2PDMSForm()
        {
            BuildUi();
            TryLoadEmbeddedIcon();            // 嵌入图标（build.cmd 的 /resource:pkpm2pdms.ico）
            PKLog.Write("form opened");       // 参照 TextForm.cs:59
        }

        // ---------------- UI construction（参照 TextForm.cs:62-72 BuildUi 分组写法） ----------------

        private GroupBox grpOp, grpIO, grpModel, grpOut, grpRun;

        private void BuildUi()
        {
            FormStyle();
            BuildOpGroup();
            BuildIoGroup();
            BuildModelGroup();
            BuildOutGroup();
            BuildRunGroup();
            BuildSummary();
            ApplyOpState();          // 构造末尾显式落一次初始状态（分组控件齐了才生效：
                                     //   建模参数启用 + 缺省输出路径），不依赖下拉事件何时触发
        }

        private void FormStyle()                                    // 参照 TextForm.cs:74-83
        {
            Text = "PKPM2PDMS v2.1.0";                               // 契约 §p.3-13 窗体标题（RENAME_MAP §4.2）
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;          // 参照 TextForm.cs:78
            ClientSize = new Size(660, 724);
            BackColor = SystemColors.Control;
            Font = new Font("Segoe UI", 9f);                         // 参照 TextForm.cs:81
            ShowInTaskbar = false;                                   // 参照 TextForm.cs:82（PDMS 拥有的工具窗体）
        }

        private void BuildOpGroup()
        {
            grpOp = new GroupBox();
            grpOp.Location = new Point(10, 8);
            grpOp.Size = new Size(640, 52);
            grpOp.Text = "操作";

            Label lblOp = new Label();
            lblOp.Text = "操作类型";
            lblOp.Location = new Point(12, 23);
            lblOp.AutoSize = true;

            cmbOp = new ComboBox();
            cmbOp.DropDownStyle = ComboBoxStyle.DropDownList;         // 契约 §p.3-1 DropDownList
            cmbOp.Location = new Point(85, 19);
            cmbOp.Size = new Size(200, 21);
            // R6 问题③：只三项（中文显示；值 = auto2pdms/pdms2pdt/pdms2jwd，见 OpItems）
            cmbOp.Items.AddRange(OpItems);
            cmbOp.SelectedIndex = 0;                                  // 缺省 PKPM导入PDMS（auto2pdms）
            cmbOp.SelectedIndexChanged += delegate { ApplyOpState(); };

            Label lblOpNote = new Label();
            lblOpNote.Text = "导入自动识别 .jwd / .pdt（按文件内容判定，不猜）";
            lblOpNote.Location = new Point(310, 22);
            lblOpNote.AutoSize = true;
            lblOpNote.ForeColor = SystemColors.GrayText;

            grpOp.Controls.Add(lblOp);
            grpOp.Controls.Add(cmbOp);
            grpOp.Controls.Add(lblOpNote);
            Controls.Add(grpOp);
        }

        private void BuildIoGroup()
        {
            grpIO = new GroupBox();
            grpIO.Location = new Point(10, 64);
            grpIO.Size = new Size(640, 118);
            grpIO.Text = "输入";

            Label lblSource = new Label();
            lblSource.Text = "源文件";
            lblSource.Location = new Point(12, 25);
            lblSource.AutoSize = true;

            txtSource = new TextBox();
            txtSource.Location = new Point(85, 21);
            txtSource.Size = new Size(440, 21);
            txtSource.TextChanged += delegate { AutoSecmap(); UpdateDefaultOut(); };

            btnBrowseSource = new Button();
            btnBrowseSource.Text = "浏览…";
            btnBrowseSource.Location = new Point(535, 19);
            btnBrowseSource.Size = new Size(90, 24);
            btnBrowseSource.Click += delegate { BrowseSource(); };

            Label lblSecmap = new Label();
            lblSecmap.Text = "截面匹配";
            lblSecmap.Location = new Point(12, 53);
            lblSecmap.AutoSize = true;

            txtSecmap = new TextBox();
            txtSecmap.Location = new Point(85, 49);
            txtSecmap.Size = new Size(440, 21);
            txtSecmap.TextChanged += delegate
            {   // 手工改成与自动预填不同 ⇒ 停止自动预填（尊重用户输入）
                if (_secmapAuto && txtSecmap.Text != _lastAutoSecmap) _secmapAuto = false;
            };

            btnBrowseSecmap = new Button();
            btnBrowseSecmap.Text = "浏览…";
            btnBrowseSecmap.Location = new Point(535, 47);
            btnBrowseSecmap.Size = new Size(90, 24);
            btnBrowseSecmap.Click += delegate { BrowseFile(txtSecmap, "截面匹配文件 (*.txt)|*.txt|全部文件 (*.*)|*.*", false); };

            chkUseExtra = new CheckBox();
            chkUseExtra.Text = "补充映射";
            chkUseExtra.Location = new Point(12, 82);
            chkUseExtra.AutoSize = true;
            chkUseExtra.Checked = true;                               // 契约 §p.3-4：缺省勾选

            txtExtra = new TextBox();
            txtExtra.Location = new Point(95, 80);
            txtExtra.Size = new Size(430, 21);
            // 留空 = 引擎自动加载 engine/secmap_extra.txt（§e.4/§f.1 同规则）

            grpIO.Controls.Add(lblSource);
            grpIO.Controls.Add(txtSource);
            grpIO.Controls.Add(btnBrowseSource);
            grpIO.Controls.Add(lblSecmap);
            grpIO.Controls.Add(txtSecmap);
            grpIO.Controls.Add(btnBrowseSecmap);
            grpIO.Controls.Add(chkUseExtra);
            grpIO.Controls.Add(txtExtra);
            Controls.Add(grpIO);
        }

        private void BuildModelGroup()
        {
            grpModel = new GroupBox();
            grpModel.Location = new Point(10, 186);
            grpModel.Size = new Size(640, 118);
            grpModel.Text = "建模参数（仅「PKPM导入PDMS」启用；数值单位 = 单位下拉，坐标公式 §f.1）";

            Label lblBase = new Label();
            lblBase.Text = "基点 ENU";
            lblBase.Location = new Point(12, 25);
            lblBase.AutoSize = true;

            numBaseE = MakeNumeric(3);                                // §p.3-5：3 位小数
            numBaseE.Location = new Point(85, 21);
            numBaseN = MakeNumeric(3);
            numBaseN.Location = new Point(190, 21);
            numBaseU = MakeNumeric(3);
            numBaseU.Location = new Point(295, 21);

            Label lblAngle = new Label();
            lblAngle.Text = "转角(度)";
            lblAngle.Location = new Point(400, 25);
            lblAngle.AutoSize = true;

            numAngle = MakeNumeric(2);                                // §p.3-6：2 位小数
            numAngle.Location = new Point(470, 21);
            numAngle.Size = new Size(80, 21);
            numAngle.Minimum = -360;
            numAngle.Maximum = 360;

            Label lblUnit = new Label();
            lblUnit.Text = "单位";
            lblUnit.Location = new Point(12, 55);
            lblUnit.AutoSize = true;

            cmbUnit = new ComboBox();
            cmbUnit.DropDownStyle = ComboBoxStyle.DropDownList;
            cmbUnit.Location = new Point(85, 51);
            cmbUnit.Size = new Size(80, 21);
            cmbUnit.Items.AddRange(new object[] { "mm", "cm", "m" }); // §p.3-7
            cmbUnit.SelectedIndex = 0;                                // 缺省 mm

            // §p.3-8：构件类别勾选（与现有 Add-in 的 Chk_Column/... 同名同义；
            // 本包把支撑拆成 HBrace/VBrace 两个）。注意：§m.1 冻结的 CLI 暂无类别过滤参数，
            // 这些勾选仅按契约保留 UI（见 README"现状与依赖"）。
            chkColumn = MakeCheck("chkColumn", "柱 Column", 200, 51);
            chkBeam = MakeCheck("chkBeam", "梁 Beam", 300, 51);
            chkHBrace = MakeCheck("chkHBrace", "水平支撑", 400, 51);
            chkVBrace = MakeCheck("chkVBrace", "竖向支撑", 500, 51);
            chkSlab = MakeCheck("chkSlab", "板 Slab", 200, 81);
            chkWall = MakeCheck("chkWall", "墙 Wall", 300, 81);
            chkGrid = MakeCheck("chkGrid", "轴网 Grid", 400, 81);
            chkHole = MakeCheck("chkHole", "洞口 Hole", 500, 81);

            grpModel.Controls.Add(lblBase);
            grpModel.Controls.Add(numBaseE);
            grpModel.Controls.Add(numBaseN);
            grpModel.Controls.Add(numBaseU);
            grpModel.Controls.Add(lblAngle);
            grpModel.Controls.Add(numAngle);
            grpModel.Controls.Add(lblUnit);
            grpModel.Controls.Add(cmbUnit);
            grpModel.Controls.Add(chkColumn);
            grpModel.Controls.Add(chkBeam);
            grpModel.Controls.Add(chkHBrace);
            grpModel.Controls.Add(chkVBrace);
            grpModel.Controls.Add(chkSlab);
            grpModel.Controls.Add(chkWall);
            grpModel.Controls.Add(chkGrid);
            grpModel.Controls.Add(chkHole);
            Controls.Add(grpModel);
        }

        private static NumericUpDown MakeNumeric(int decimals)
        {
            NumericUpDown n = new NumericUpDown();
            n.DecimalPlaces = decimals;
            n.Minimum = -100000000;
            n.Maximum = 100000000;
            n.Value = 0;
            n.Size = new Size(95, 21);
            return n;
        }

        private CheckBox MakeCheck(string name, string text, int x, int y)
        {
            CheckBox c = new CheckBox();
            c.Name = name;
            c.Text = text;
            c.Location = new Point(x, y);
            c.AutoSize = true;
            c.Checked = true;
            return c;
        }

        private void BuildOutGroup()
        {
            grpOut = new GroupBox();
            grpOut.Location = new Point(10, 308);
            grpOut.Size = new Size(640, 56);
            grpOut.Text = "输出";

            Label lblOut = new Label();
            lblOut.Text = "输出文件";
            lblOut.Location = new Point(12, 23);
            lblOut.AutoSize = true;

            txtOut = new TextBox();
            txtOut.Location = new Point(85, 19);
            txtOut.Size = new Size(440, 21);
            txtOut.TextChanged += delegate
            {   // 手工改成与自动预填不同 ⇒ 停止自动预填（尊重用户输入；同 txtSecmap 的处理）
                if (_outAuto && txtOut.Text != _lastAutoOut) _outAuto = false;
            };

            btnBrowseOut = new Button();
            btnBrowseOut.Text = "浏览…";
            btnBrowseOut.Location = new Point(535, 17);
            btnBrowseOut.Size = new Size(90, 24);
            btnBrowseOut.Click += delegate { BrowseOut(); };

            grpOut.Controls.Add(lblOut);
            grpOut.Controls.Add(txtOut);
            grpOut.Controls.Add(btnBrowseOut);
            Controls.Add(grpOut);
        }

        private void BuildRunGroup()
        {
            grpRun = new GroupBox();
            grpRun.Location = new Point(10, 368);
            grpRun.Size = new Size(640, 56);
            grpRun.Text = "执行";

            btnRun = new Button();
            btnRun.Text = "执行";
            btnRun.Location = new Point(12, 17);
            btnRun.Size = new Size(120, 30);
            btnRun.Click += delegate { RunClicked(); };

            progressBar1 = new ProgressBar();                        // §p.3-11
            progressBar1.Location = new Point(150, 22);
            progressBar1.Size = new Size(330, 20);

            btnOpenReport = new Button();                            // §p.3-12
            btnOpenReport.Text = "打开报告";
            btnOpenReport.Location = new Point(500, 17);
            btnOpenReport.Size = new Size(120, 30);
            btnOpenReport.Enabled = false;
            btnOpenReport.Click += delegate { OpenReport(); };

            grpRun.Controls.Add(btnRun);
            grpRun.Controls.Add(progressBar1);
            grpRun.Controls.Add(btnOpenReport);
            Controls.Add(grpRun);

            _progTimer = new System.Windows.Forms.Timer();
            _progTimer.Interval = 100;
            _progTimer.Tick += delegate
            {
                if (_running)
                    progressBar1.Value = (progressBar1.Value + 2) % 100;   // 等待期滚动
            };
            _progTimer.Start();
        }

        private void BuildSummary()
        {
            txtSummary = new TextBox();                              // §p.3-11：多行只读摘要
            txtSummary.Multiline = true;
            txtSummary.ReadOnly = true;
            txtSummary.ScrollBars = ScrollBars.Vertical;
            txtSummary.Location = new Point(10, 430);
            txtSummary.Size = new Size(640, 264);
            txtSummary.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
            txtSummary.WordWrap = false;
            Controls.Add(txtSummary);
        }

        // ---------------- 状态联动 ----------------

        // R6 问题③：三项的两类（导入 = 建模方向，生成宏并**立即执行**；导出 = 先取 PDMSDUMP）
        private static readonly string[] ModelingOps = new string[] { "auto2pdms" };
        private static readonly string[] ExportOps = new string[] { "pdms2jwd", "pdms2pdt" };

        private static string OutExtFor(string op)
        {
            switch (op)
            {
                case "auto2pdms": return ".mac";        // 导入的"输出"= 引擎生成的宏（审计留档）
                case "pdms2jwd": return ".jwd";
                case "pdms2pdt": return ".pdt";
                default: return ".mac";
            }
        }

        private string CurrentOp()
        {
            OpItem it = cmbOp.SelectedItem as OpItem;
            return it == null ? "auto2pdms" : it.Op;      // 缺省 = PKPM导入PDMS
        }

        private bool IsModelingOp(string op)
        {
            return Array.IndexOf(ModelingOps, op) >= 0;
        }

        private void ApplyOpState()
        {
            string op = CurrentOp();
            grpModel.Enabled = IsModelingOp(op);      // §p.3-5/6/8：仅导入方向启用建模参数
            UpdateDefaultOut();
        }

        private void AutoSecmap()
        {
            if (!_secmapAuto) return;
            string src = txtSource.Text.Trim();
            if (src.Length == 0) return;
            try
            {
                string dir = Path.GetDirectoryName(src);
                if (dir == null) return;
                _lastAutoSecmap = Path.Combine(dir, DefaultSecmapName);  // 契约 §p.3-3/§f.1 同规则
                txtSecmap.Text = _lastAutoSecmap;
            }
            catch { }
        }

        // R6 问题②：导入方向的宏由引擎写到临时目录（用户不接触宏文件），文件名带时间戳
        //   —— 每次执行留一份审计产物，不覆盖上一份。
        private void UpdateDefaultOut()
        {
            if (!_outAuto) return;                     // 用户改过 ⇒ 不再覆盖
            string op = CurrentOp();
            string src = txtSource.Text.Trim();
            string baseName = "out";
            if (src.Length > 0)
            {
                try { baseName = Path.GetFileNameWithoutExtension(src); }
                catch { }
            }
            if (baseName.Length == 0) baseName = "out";
            string dir = Path.Combine(Path.GetTempPath(), "PKPM2PDMS");
            string name = IsModelingOp(op)
                ? "import_" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".mac"
                : baseName + OutExtFor(op);
            _lastAutoOut = Path.Combine(dir, name);    // 先记再赋值（TextChanged 据此判"非手工"）
            txtOut.Text = _lastAutoOut;                // 契约 §p.3-9 缺省
        }

        // ---------------- 文件浏览 ----------------

        private static void BrowseFile(TextBox target, string filter, bool save)
        {
            if (save)
            {
                SaveFileDialog d = new SaveFileDialog();
                d.Filter = filter;
                if (d.ShowDialog() == DialogResult.OK) target.Text = d.FileName;
            }
            else
            {
                OpenFileDialog d = new OpenFileDialog();
                d.Filter = filter;
                if (d.ShowDialog() == DialogResult.OK) target.Text = d.FileName;
            }
        }

        private void BrowseSource()
        {
            // R6 问题③：导入按内容自动识别 ⇒ 文件选择同时接受 .jwd 与 .pdt
            BrowseFile(txtSource,
                "PKPM 模型 (*.jwd;*.pdt)|*.jwd;*.pdt|PKPM 模型 (*.jwd)|*.jwd"
                + "|PKPM 中间模型 (*.pdt)|*.pdt|全部文件 (*.*)|*.*",
                false);
            _secmapAuto = true;
            AutoSecmap();
            UpdateDefaultOut();
        }

        private void BrowseOut()
        {
            string ext = OutExtFor(CurrentOp());
            BrowseFile(txtOut,
                "输出文件 (*" + ext + ")|*" + ext + "|全部文件 (*.*)|*.*", true);
        }

        // ---------------- 执行（契约 §p.5 序列 ①-⑤） ----------------

        private void RunClicked()
        {
            if (_running) return;

            // ① 校验输入存在（§p.5 ①）
            string err = ValidateInputs();
            if (err != null)
            {
                // R6：校验不过也**不弹窗**（"执行"路径全程无第二个窗口），落摘要区 + 日志
                PKLog.Write("validate failed: " + err.Replace("\n", " "));
                txtSummary.Text = "== 输入校验未通过（未执行）==\n" + err;
                return;
            }

            string op = CurrentOp();
            string outPath = txtOut.Text.Trim();
            string dumpPath = "";
            string outDir = Path.GetDirectoryName(outPath);
            if (outDir != null && outDir.Length > 0)
            {
                try { Directory.CreateDirectory(outDir); }
                catch (Exception ex) { PKLog.Write("create out dir failed: " + ex.Message); }
            }

            // 导出方向（pdms2jwd/pdms2pdt）：先取 PDMSDUMP（§p.5 导出方向条）。
            // 源框给出已有 dump 则直接用之；否则调 PML 导出函数现场生成
            //   （!!pkpm2pdmsexport 入口见 pdms\pkpm2pdmsexport.pmlfnc:4；
            //   输出 = <输出基名>.dump.txt）。PML 必须在 UI 线程执行。
            if (Array.IndexOf(ExportOps, op) >= 0)
            {
                string src = txtSource.Text.Trim();
                if (src.Length > 0 && File.Exists(src))
                {
                    dumpPath = src;
                }
                else
                {
                    dumpPath = Path.Combine(
                        Path.GetDirectoryName(outPath),
                        Path.GetFileNameWithoutExtension(outPath) + ".dump.txt");
                    string r = PmlBridge.RunPmlWithResult(
                        "!r = !!pkpm2pdmsexport(!!CE, '" + dumpPath + "')");
                    // 〔R6 实机修复〕同 RunImportMacro：CreateCommand().Result 对 PML 表达式命令
                    //   取不到返回值（实机 2026-09-28 16:55/17:20 两次证据），故不能拿 r 判成败。
                    //   导出成功的**可验证判据 = dump 文件真的写出来了且非空**（引擎下一步就吃它）。
                    bool dumpOk = false;
                    try { dumpOk = File.Exists(dumpPath) && new FileInfo(dumpPath).Length > 0; }
                    catch (Exception) { dumpOk = false; }
                    PKLog.Write("pml export dump=" + dumpPath + " exists=" + dumpOk
                        + " r=" + (r == null ? "(null)" : r));
                    if (!dumpOk)
                    {
                        // R6：失败**不弹窗**（"执行"之后只刷新窗体自身结果），落摘要区 + 日志
                        string msg = "PDMS 导出失败（!!pkpm2pdmsexport）：\n"
                            + (r == null ? "PML 调用未回传文本" : r)
                            + "\n未生成 PDMSDUMP 文件：" + dumpPath
                            + "\n请确认当前 CE 为要导出的 SITE/ZONE。";
                        PKLog.Write("pml export failed: " + r);
                        txtSummary.Text = msg;
                        return;
                    }
                }
            }

            txtSummary.Text = "";
            btnOpenReport.Enabled = false;
            SetBusy(true);
            _runError = "";
            _result = null;
            _reportPath = ReportPathFor(outPath);

            // ②〔R7〕SITE 名探测（导入方向）：执行前在 .NET 侧**直查试名**，静默零弹窗。
            //   试出的可用名经 --request 的 site_name 键传给引擎（引擎原样使用、不改名）。
            //   碰 PDMS 库的动作一律在 UI 线程上做（与下面 PML 导出调用同规矩）。
            _siteName = "";
            if (IsModelingOp(op))
            {
                SiteProbeResult probe = SiteProber.ProbeFirstFree();
                PKLog.Write("site probe: mode=" + probe.Mode + " found=" + probe.Found
                    + " name=" + probe.SiteName + " tried=" + probe.Tried);
                if (!probe.Found)
                {
                    // 用户方案第 1 条：全部候选都被占用 / 探测机制不可用 ⇒ 明确报错、**不执行导入**
                    //   （结果区提示不算弹窗违规；"执行"路径不弹任何窗口）
                    StringBuilder fail = new StringBuilder();
                    fail.AppendLine("== 未执行：SITE 名探测失败 ==");
                    fail.AppendLine(probe.Detail);
                    fail.AppendLine("探测机制：" + probe.Mode + "；候选序列：/PKPM2PDMS → "
                        + "/PKPM2PDMSre → … re99（共 100 个）");
                    for (int i = 0; i < probe.Notes.Count; i++)
                        fail.AppendLine("说明：" + probe.Notes[i]);
                    txtSummary.Text = fail.ToString();
                    SetBusy(false);
                    return;
                }
                _siteName = probe.SiteName;
            }

            Dictionary<string, object> args = BuildEngineArgs(op, dumpPath);
            string tool = op;
            _worker = new Thread(new ThreadStart(delegate
            {
                try
                {
                    _result = EngineRunner.Run(tool, args);   // ②③ 写 request + 进程等待
                }
                catch (Exception ex)
                {
                    _runError = ex.ToString();
                }
                finally
                {
                    try { BeginInvoke(new MethodInvoker(JobDone)); }
                    catch (Exception) { SetBusy(false); }
                }
            }));
            _worker.IsBackground = true;
            _worker.Start();
        }

        private void SetBusy(bool busy)
        {
            _running = busy;
            btnRun.Enabled = !busy;
            UseWaitCursor = busy;
            if (!busy) progressBar1.Value = 0;
        }

        private static string ReportPathFor(string outPath)
        {
            return Path.Combine(Path.GetDirectoryName(outPath),
                Path.GetFileNameWithoutExtension(outPath) + ".report.json");   // §f.1 --report 缺省规则
        }

        private string ValidateInputs()
        {
            string op = CurrentOp();
            string src = txtSource.Text.Trim();
            string outPath = txtOut.Text.Trim();

            bool needsSource = Array.IndexOf(ExportOps, op) < 0;
            if (needsSource)
            {
                if (src.Length == 0)
                    return "请选择源文件（PKPM 模型 .jwd 或 .pdt）。";
                if (!File.Exists(src))
                    return "源文件不存在：\n" + src;
                // R6 问题③：导入方向按**文件内容**自动识别（.jwd = SQLite / .pdt = 文本），
                //   故不按扩展名拦截；不像 .jwd 也不像 .pdt 时由引擎明确报错（不猜）。
            }
            else if (src.Length > 0 && !File.Exists(src))
            {
                return "指定的 PDMSDUMP 文本不存在：\n" + src;
            }

            if (outPath.Length == 0) return "请指定输出文件。";
            if (src.Length > 0
                && string.Equals(Path.GetFullPath(outPath), Path.GetFullPath(src),
                    StringComparison.OrdinalIgnoreCase))
                return "输出文件不能与源文件相同。";
            return null;
        }

        // 组装 engine request 的 args（§p.5：键名与 CLI 一致 —— 键 = 长选项名去 "--"）。
        // 每个操作只传 §m.1 该子命令实际存在的参数；不存在的选项绝不发明。
        private Dictionary<string, object> BuildEngineArgs(string op, string dumpPath)
        {
            Dictionary<string, object> a = new Dictionary<string, object>();
            string src = txtSource.Text.Trim();
            string outPath = txtOut.Text.Trim();

            // 源位置参数（positional，与 CLI 子命令的位置参数同名）
            switch (op)
            {
                // R6 问题③：auto2pdms（自动识别 .jwd/.pdt）的位置参数 dest = "src"
                //   —— 与 jwd2pdms 的 "jwd" / pdt2pdms 的 "pdt" 同一落位约定
                //   （cli.py:2264-2272 按子命令自己的位置 dest 落位）。
                case "auto2pdms": a["src"] = src; break;
                case "pdms2jwd": case "pdms2pdt": a["dump"] = dumpPath; break;
            }
            a["out"] = outPath;
            a["report"] = _reportPath;

            if (txtSecmap.Text.Trim().Length > 0) a["secmap"] = txtSecmap.Text.Trim();

            // --extra：仅接受该选项的子命令（auto2pdms 沿 jwd2pdms/pdt2pdms 的选项集）
            bool hasExtra = (op == "auto2pdms");
            if (hasExtra && chkUseExtra.Checked && txtExtra.Text.Trim().Length > 0)
                a["extra"] = txtExtra.Text.Trim();
            // 勾选但留空 = 引擎按 §e.4 缺省自动加载 engine/secmap_extra.txt（省略参数）
            // 未勾选：CLI 无禁用开关（§f.1），同样省略 —— 差异记入 README。

            if (IsModelingOp(op))
            {
                // 〔R7〕site_name：SITE 名（.NET 侧直查试出的可用名，引擎原样使用、不做 re 逻辑）。
                //   键名 = CLI 长选项 --site-name 的 dest（引擎 cli.py 的 site_name 键约定）。
                a["site_name"] = _siteName;
                // --base 三元组（单位 = cmbUnit）；--angle 度；--unit 只缩放宏内数值（§d.4-1）
                a["base"] = new string[] {
                    numBaseE.Value.ToString(System.Globalization.CultureInfo.InvariantCulture),
                    numBaseN.Value.ToString(System.Globalization.CultureInfo.InvariantCulture),
                    numBaseU.Value.ToString(System.Globalization.CultureInfo.InvariantCulture) };
                a["angle"] = numAngle.Value.ToString(System.Globalization.CultureInfo.InvariantCulture);
                a["unit"] = (string)cmbUnit.SelectedItem;
            }
            return a;
        }

        // ④⑤ 完成处理（UI 线程）：退出码 !=0 报错+日志；=0 且导入方向立即执行宏并取回改名。
        // R6：本方法**不弹任何窗口**（"执行"之后只刷新窗体自身结果），失败一律落摘要区 + addin.log。
        private void JobDone()
        {
            SetBusy(false);

            if (_runError.Length > 0)
            {
                PKLog.Write("job error: " + _runError);
                txtSummary.Text = "== 执行异常 ==\n" + _runError;
                return;
            }
            EngineResult r = _result;
            if (r == null) return;

            StringBuilder sum = new StringBuilder();
            if (r.EntryMissing || r.TimedOut || r.ExitCode != 0)
            {
                // §p.5 ④ / §o.6-3：退出码 !=0 ⇒ 报错 + 日志（绝不静默跳过）。
                // R6：报错**不进弹窗**（"执行"之后只刷新窗体自身结果），摘要区整段给全 + addin.log。
                PKLog.Write("engine failed: exit=" + r.ExitCode + " timedOut=" + r.TimedOut
                    + " entryMissing=" + r.EntryMissing + " err=" + r.StdErr);
                string msg = "== 执行失败：引擎退出码 " + r.ExitCode + " ==";
                if (r.EntryMissing) msg += "\n找不到引擎入口（engine/dist 由实施包 S9 交付；"
                    + "可用环境变量 PKPM2PDMS_ENGINE 指定）";
                if (r.TimedOut) msg += "\n等待超时（30 分钟）";
                sum.AppendLine(msg);
                sum.AppendLine(Truncate(r.StdErr, 1500));
                sum.Append(Truncate(r.StdOut, 2000));
                txtSummary.Text = sum.ToString();
                return;
            }

            sum.Append(r.StdOut);      // §p.5：stdout = 一行摘要 + 未解析清单（UTF-8）

            string op = CurrentOp();
            if (IsModelingOp(op))
            {
                // ④⑤ R7 一键导入：宏刚由引擎写到临时目录 ⇒ 立即在 PDMS 内 `$M` 执行，
                //   用户全程不接触宏文件；结果（成功/失败 + 构件计数 + 命名结果）上摘要区。
                string mac = txtOut.Text.Trim();
                ExecMacro(sum, mac);
            }

            btnOpenReport.Enabled = File.Exists(_reportPath);
            txtSummary.Text = sum.ToString();
        }

        // 〔R7〕导入宏的执行入口 = `$M '<宏全路径>'`（用户方案第 8 条执行链的最后一环）。
        //   $M 执行 .mac 是合法形态，官方先例（本机只读证据）：
        //     * PMLLIB 的 common\forms\*macro*.pmlfrm:76-86 —— `$m "$!this.<成员>"`（宏路径由表单成员给）
        //     * mypml\HCD-TOOL\...\yhcopyitemstoanywhere.pmlfrm 同款 $M 用法
        //   为什么不再走 PML 运行入口函数：R7 起该族 PML 函数整体退役（不再部署、不再被任何代码
        //   引用，见 deploy_pkpm2pdms.py 的 RETIRED_PML）；入口函数唯一的价值是"预载唯一化函数"，
        //   而唯一化已改为「.NET 侧探测 SITE 名 + 引擎生成期查重」，宏里不再需要任何 PML 函数。
        //   为什么绝不 $M <...>.pmlfnc：本机实测 $M 文件形式的 .pmlfnc 报 (46,80) PML:
        //     Invalid syntax（.pmlfnc 只按「文件名 = 函数名」由 PMLLIB 自动加载）。
        //   路径用单引号包裹；PML 单引号串无转义 ⇒ 含单引号时明确拒绝执行（不猜、不半执行）。
        private void ExecMacro(StringBuilder sum, string mac)
        {
            if (mac.IndexOf('\'') >= 0)
            {
                sum.AppendLine("== 未执行：输出宏路径含单引号，PML 字符串无法安全转义 ==");
                sum.AppendLine(mac);
                PKLog.Write("macro path contains a single quote, refuse PML call");
                return;
            }

            PKLog.Write("run macro: $M '" + mac + "'");
            bool ok = PmlBridge.RunPml("$M '" + mac + "'");   // 失败详情由 PmlBridge 落 addin.log
            if (ok)
            {
                sum.AppendLine("宏已在 PDMS 中执行（$M）：" + mac);
            }
            else
            {
                // 报错不静默（本窗只刷新摘要区 + addin.log，不弹窗）
                sum.AppendLine("== 宏执行失败（$M 返回错误）==");
                sum.AppendLine(mac);
                sum.AppendLine("详见 addin.log 与命令窗内的报错行（宏头是 ONERROR CONTINUE，"
                    + "宏内错误不会中止后续行，故请以命令窗输出为准）。");
            }

            // SITE 存在性复核（同一套静默直查）：既是"宏真的建了 SITE"的正向对照，
            //   也是探测机制"能看见已存在元素"的一次反向验证 —— 两种结果都如实上窗。
            if (_siteName.Length > 0)
                sum.AppendLine("SITE 复核（" + _siteName + "）：" + SiteProber.VerifySiteExists(_siteName));

            AppendEngineNames(sum);
        }

        // 〔R7〕命名结果（取代 R6 从 PML 全局量取改名记录的老路）：读引擎 report.json 的
        //   options.site_name（本次 SITE 名 = .NET 探测结果的唯一真相）、
        //   stats.used_names_count（宏内**带名**创建用掉的名字数，引擎生成期已查重）、
        //   stats.unnamed_count（无名创建 = SCTN/PANE/STWALL 条数）。
        //   报告是 UTF-8 无 BOM + LF（§g/§h），这里只做最小解析，不引入 JSON 库依赖。
        private void AppendEngineNames(StringBuilder sum)
        {
            try
            {
                if (_reportPath.Length == 0 || !File.Exists(_reportPath)) return;
                string text = File.ReadAllText(_reportPath, new UTF8Encoding(false));
                string site = JsonStrAfter(text, "site_name");
                string used = JsonIntAfter(text, "used_names_count");
                string unnamed = JsonIntAfter(text, "unnamed_count");
                if (site == null && used == null && unnamed == null) return;
                sum.AppendLine("引擎报告命名结果（" + _reportPath + "）：");
                if (site != null) sum.AppendLine("  SITE 名（.NET 探测，引擎原样使用）：" + site);
                if (used != null) sum.AppendLine("  带名创建的名字数（生成期已查重）：" + used);
                if (unnamed != null) sum.AppendLine("  无名创建（SCTN/PANE/STWALL）：" + unnamed + " 个");
            }
            catch (Exception ex)
            {
                PKLog.Write("read report names failed: " + ex.Message);
            }
        }

        // 取 "键": <整数> 的字面量；找不到返回 null（报告形状由引擎固定，够用即可）。
        private static string JsonIntAfter(string text, string key)
        {
            int i = text.IndexOf("\"" + key + "\"", StringComparison.Ordinal);
            if (i < 0) return null;
            int c = text.IndexOf(':', i);
            if (c < 0) return null;
            int s = c + 1;
            while (s < text.Length && (text[s] == ' ' || text[s] == '\t')) s++;
            int e = s;
            while (e < text.Length && (char.IsDigit(text[e]) || text[e] == '-')) e++;
            return e > s ? text.Substring(s, e - s) : null;
        }

        // 取 "键": "字符串" 的内容；找不到返回 null。只解 \" 与 \\ 两种转义（引擎写的值里
        //   实际只可能出现这两者；其余原样返回，不猜）。
        private static string JsonStrAfter(string text, string key)
        {
            int i = text.IndexOf("\"" + key + "\"", StringComparison.Ordinal);
            if (i < 0) return null;
            int c = text.IndexOf(':', i);
            if (c < 0) return null;
            int s = c + 1;
            while (s < text.Length && (text[s] == ' ' || text[s] == '\t')) s++;
            if (s >= text.Length || text[s] != '"') return null;
            s++;
            StringBuilder o = new StringBuilder();
            for (int p = s; p < text.Length; p++)
            {
                char ch = text[p];
                if (ch == '\\' && p + 1 < text.Length)
                {
                    char n = text[p + 1];
                    if (n == '"' || n == '\\') { o.Append(n); p++; continue; }
                    o.Append(ch);
                    continue;
                }
                if (ch == '"') return o.ToString();
                o.Append(ch);
            }
            return null;
        }

        private static string Truncate(string s, int max)
        {
            if (s == null) return "";
            if (s.Length <= max) return s;
            return s.Substring(0, max) + "\n…(截断)";
        }

        // §p.3-12：用系统默认程序打开 report.json
        private void OpenReport()
        {
            try
            {
                if (_reportPath.Length > 0 && File.Exists(_reportPath))
                    System.Diagnostics.Process.Start(_reportPath);
                else
                    MessageBox.Show("报告尚未生成：" + _reportPath, "PKPM2PDMS导入导出");
            }
            catch (Exception ex)
            {
                MessageBox.Show("打开报告失败：\n" + ex.Message, "PKPM2PDMS导入导出");
            }
        }

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            if (_progTimer != null) _progTimer.Stop();
            base.OnFormClosed(e);
        }

        // 窗体图标：build.cmd 用 /resource:"<ico>",pkpm2pdms.ico 把图标嵌进程序集，
        // 这里按该逻辑名取回。图标是 C 包的产物；缺失时**不影响任何既有行为**——
        // 静默保持 WinForms 缺省图标（同源写法：TGSPECAddin.cs 的图标嵌入用法）。
        private void TryLoadEmbeddedIcon()
        {
            try
            {
                Stream s = typeof(PKPM2PDMSForm).Assembly
                    .GetManifestResourceStream("pkpm2pdms.ico");
                if (s == null)
                {
                    PKLog.Write("embedded icon absent (build without /resource:), keep default");
                    return;
                }
                using (s) { Icon = new Icon(s); }
            }
            catch (Exception ex)
            {
                PKLog.Write("embedded icon load failed: " + ex.Message);
            }
        }
    }
}

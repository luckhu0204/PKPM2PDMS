// PKPMJWDForm.cs - PKPM JWD import/export tool window (WinForms, non-modal singleton).
// 控件清单冻结：契约 CONTRACT.md §p.3 的 13 项表（控件名逐一对应，不得增删语义）。
// 窗体写法参照：D:\AI_Work\PDMS三维文字程序\TGTEXT\TextForm.cs
//   （13 public class TextForm : Form；:55-60 构造器 BuildUi；:74-83 FormStyle：
//   StartPosition/ShowInTaskbar=false 工具窗体；:29 控件声明分组注释风格）。
// 执行序列冻结：契约 §p.5 ①-⑤（校验 -> 写 request -> 进程等待 -> $M+取回改名 -> 摘要上窗）。
// 混写红线（§p.4）：本窗体不读写 .jwd/.pdt —— 格式转换全部由引擎进程完成；
//   PDMS 库内动作（导出 PML / $M 执行宏 / 取回改名记录）全部经 PmlBridge。
using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Text;
using System.Threading;
using System.Windows.Forms;

namespace PKPMJWD
{
    public class PKPMJWDForm : Form
    {
        // ---- §p.3 #1：操作下拉（10 个窗体子命令；dbsections 不进窗体） ----
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

        private const string DefaultSecmapName = "PKPM转PDMS截面匹配文件.txt";   // 契约 §f.1 同规则

        public PKPMJWDForm()
        {
            BuildUi();
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
        }

        private void FormStyle()                                    // 参照 TextForm.cs:74-83
        {
            Text = "PKPM JWD 导入导出";                              // 契约 §p.3-13 窗体标题
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
            // §p.3-1 的 10 个操作（§m.1 子集；dbsections 不进窗体）
            cmbOp.Items.AddRange(new object[] {
                "jwd2pdms", "pdt2pdms", "pdms2jwd", "pdms2pdt",
                "jwd2db", "pdt2db", "db2jwd", "db2pdt",
                "jwd2pdt", "pdt2jwd" });
            cmbOp.SelectedIndex = 0;                                  // 缺省 jwd2pdms
            cmbOp.SelectedIndexChanged += delegate { ApplyOpState(); };

            Label lblOpNote = new Label();
            lblOpNote.Text = "源类型按扩展名判定（不设格式下拉）";
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
            grpModel.Text = "建模参数（仅 *2pdms 启用；数值单位 = 单位下拉，坐标公式 §f.1）";

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
            txtOut.TextChanged += delegate { };     // 允许手改；换源时自动重设

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

        private static readonly string[] ModelingOps = new string[] { "jwd2pdms", "pdt2pdms" };
        private static readonly string[] ExportOps = new string[] { "pdms2jwd", "pdms2pdt" };

        private static string OutExtFor(string op)
        {
            switch (op)
            {
                case "jwd2pdms": case "pdt2pdms": case "jwd2db": case "pdt2db": return ".mac";
                case "pdms2jwd": case "db2jwd": case "pdt2jwd": return ".jwd";
                case "pdms2pdt": case "db2pdt": case "jwd2pdt": return ".pdt";
                default: return ".mac";
            }
        }

        private static string RequiredSourceExt(string op)
        {
            switch (op)
            {
                case "jwd2pdms": case "jwd2db": case "jwd2pdt": return ".jwd";
                case "pdt2pdms": case "pdt2db": case "pdt2jwd": return ".pdt";
                default: return "";               // pdms2*/db2*：文本类，不按扩展名强制
            }
        }

        private string CurrentOp()
        {
            return cmbOp.SelectedItem == null ? "jwd2pdms" : (string)cmbOp.SelectedItem;
        }

        private bool IsModelingOp(string op)
        {
            return Array.IndexOf(ModelingOps, op) >= 0;
        }

        private void ApplyOpState()
        {
            string op = CurrentOp();
            grpModel.Enabled = IsModelingOp(op);      // §p.3-5/6/8：仅建模方向启用
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

        private void UpdateDefaultOut()
        {
            string op = CurrentOp();
            string src = txtSource.Text.Trim();
            string baseName = "out";
            if (src.Length > 0)
            {
                try { baseName = Path.GetFileNameWithoutExtension(src); }
                catch { }
            }
            if (baseName.Length == 0) baseName = "out";
            string dir = Path.Combine(Path.GetTempPath(), "PKPMJWD");
            txtOut.Text = Path.Combine(dir, baseName + OutExtFor(op));   // 契约 §p.3-9 缺省
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
            BrowseFile(txtSource,
                "PKPM 模型 (*.jwd)|*.jwd|PKPM 中间模型 (*.pdt)|*.pdt|文本 (*.txt)|*.txt|全部文件 (*.*)|*.*",
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

            // ① 校验输入存在 / 扩展名合法（§p.5 ①）
            string err = ValidateInputs();
            if (err != null)
            {
                MessageBox.Show(err, "PKPM JWD 导入导出");
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
            //   （!!pkpmjwdexport 入口见 pdms\pkpmjwdexport.pmlfnc:4；
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
                        "!r = !!pkpmjwdexport(!!CE, '" + dumpPath + "')");
                    if (r == null || !r.StartsWith("OK|"))
                    {
                        MessageBox.Show("PDMS 导出失败（!!pkpmjwdexport）：\n"
                            + (r == null ? "PML 调用失败，详见 addin.log" : r)
                            + "\n请确认当前 CE 为要导出的 SITE/ZONE。",
                            "PKPM JWD 导入导出");
                        PKLog.Write("pml export failed: " + r);
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
                    return "请选择源文件。";
                if (!File.Exists(src))
                    return "源文件不存在：\n" + src;
                string reqExt = RequiredSourceExt(op);
                if (reqExt.Length > 0
                    && !string.Equals(Path.GetExtension(src), reqExt, StringComparison.OrdinalIgnoreCase))
                    return "操作 " + op + " 要求 " + reqExt + " 源文件，当前是：\n" + src;
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
                case "jwd2pdms": case "jwd2db": case "jwd2pdt": a["jwd"] = src; break;
                case "pdt2pdms": case "pdt2db": case "pdt2jwd": a["pdt"] = src; break;
                case "pdms2jwd": case "pdms2pdt": a["dump"] = dumpPath; break;
                case "db2jwd": case "db2pdt": a["db"] = src; break;
            }
            a["out"] = outPath;
            a["report"] = _reportPath;

            if (txtSecmap.Text.Trim().Length > 0) a["secmap"] = txtSecmap.Text.Trim();

            // --extra：仅接受该选项的子命令（jwd2pdms/pdt2pdms/jwd2db/pdt2db/jwd2pdt）
            bool hasExtra = (op == "jwd2pdms" || op == "pdt2pdms" || op == "jwd2db"
                || op == "pdt2db" || op == "jwd2pdt");
            if (hasExtra && chkUseExtra.Checked && txtExtra.Text.Trim().Length > 0)
                a["extra"] = txtExtra.Text.Trim();
            // 勾选但留空 = 引擎按 §e.4 缺省自动加载 engine/secmap_extra.txt（省略参数）
            // 未勾选：CLI 无禁用开关（§f.1），同样省略 —— 差异记入 README。

            if (IsModelingOp(op))
            {
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

        // ④⑤ 完成处理（UI 线程）：退出码 !=0 弹错+日志；=0 且建模方向 $M 执行宏并取回改名。
        private void JobDone()
        {
            SetBusy(false);

            if (_runError.Length > 0)
            {
                PKLog.Write("job error: " + _runError);
                MessageBox.Show("执行异常：\n" + _runError, "PKPM JWD 导入导出");
                txtSummary.Text = _runError;
                return;
            }
            EngineResult r = _result;
            if (r == null) return;

            StringBuilder sum = new StringBuilder();
            if (r.EntryMissing || r.TimedOut || r.ExitCode != 0)
            {
                // §p.5 ④ / §o.6-3：退出码 !=0 ⇒ 弹错 + 日志（绝不静默跳过）
                PKLog.Write("engine failed: exit=" + r.ExitCode + " timedOut=" + r.TimedOut
                    + " entryMissing=" + r.EntryMissing + " err=" + r.StdErr);
                string msg = "引擎执行失败（退出码 " + r.ExitCode + "）";
                if (r.EntryMissing) msg += "\n找不到引擎入口（engine/dist 由实施包 S9 交付；"
                    + "可用环境变量 PKPMJWD_ENGINE 指定）";
                if (r.TimedOut) msg += "\n等待超时（30 分钟）";
                msg += "\n\n" + Truncate(r.StdErr, 1500) + "\n" + Truncate(r.StdOut, 500);
                MessageBox.Show(msg, "PKPM JWD 导入导出");
                sum.AppendLine("== 执行失败 ==");
                sum.AppendLine(r.StdErr);
                sum.Append(r.StdOut);
                txtSummary.Text = sum.ToString();
                return;
            }

            sum.Append(r.StdOut);      // §p.5：stdout = 一行摘要 + 未解析清单（UTF-8）

            string op = CurrentOp();
            if (IsModelingOp(op))
            {
                // ④ 建模方向：$M 执行引擎生成的宏（宏内含 §o 唯一化调用与 ONERROR 尾）。
                //   $M 绝对路径直跑 .mac 的形态同 nucdesmanchor.mac:9-11（§12#28 待实机确认）。
                string mac = txtOut.Text.Trim();
                bool ok = PmlBridge.RunPml("$M " + mac);
                if (ok)
                {
                    sum.AppendLine("宏已在 PDMS 中执行：" + mac);
                    FetchRenames(sum);
                }
                else
                {
                    // §o.6：宏失败 ⇒ 报错不静默（宏自身的 ONERROR/RETURN ERROR 会上抛到 Result）
                    MessageBox.Show("宏执行失败（PDMS 返回错误）：\n" + mac
                        + "\n详见 addin.log 与宏内报错行。", "PKPM JWD 导入导出");
                    sum.AppendLine("宏执行失败：" + mac);
                }
            }
            else if (op == "jwd2db" || op == "pdt2db")
            {
                sum.AppendLine("目录/规格宏已生成，请在 PDMS 中确认后手动执行：" + txtOut.Text.Trim());
            }

            btnOpenReport.Enabled = File.Exists(_reportPath);
            txtSummary.Text = sum.ToString();
        }

        // 取回 !!pkpmjwdRenames（§o.6-3/§o.7：report.renames 是唯一真相）。
        // 【待实机确认】CreateCommand().Result 对 PML 数组表达式的返回形态未实测
        //   （recon §3.5A 只证 $M 宏调用后可读 Result）；先原样上窗 + 落 <out>.renames.txt。
        private void FetchRenames(StringBuilder sum)
        {
            try
            {
                string ren = PmlBridge.RunPmlWithResult("!!pkpmjwdRenames");
                if (string.IsNullOrEmpty(ren)) return;
                string path = _reportPath + ".renames.txt";
                File.WriteAllText(path, ren, new UTF8Encoding(false));
                sum.AppendLine("重名唯一化记录（" + path + "）：");
                sum.AppendLine(Truncate(ren, 2000));
            }
            catch (Exception ex)
            {
                PKLog.Write("fetch renames failed: " + ex.Message);
            }
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
                    MessageBox.Show("报告尚未生成：" + _reportPath, "PKPM JWD 导入导出");
            }
            catch (Exception ex)
            {
                MessageBox.Show("打开报告失败：\n" + ex.Message, "PKPM JWD 导入导出");
            }
        }

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            if (_progTimer != null) _progTimer.Stop();
            base.OnFormClosed(e);
        }
    }
}

import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="تحليل النواقص", layout="wide")
st.title("تحليل النواقص في بيانات الموظفين")
st.markdown("### يرجى رفع ملفي البيانات للمقارنة:")

# رفع الملفات
col1, col2 = st.columns(2)
with col1:
    old_file = st.file_uploader("📁 ملف النظام القديم (ERP)", type=["xlsx"], key="old")
with col2:
    new_file = st.file_uploader("📁 ملف النظام الجديد (Cloud)", type=["xlsx"], key="new")

if old_file and new_file:
    # قراءة أسماء الأوراق
    old_sheets = pd.ExcelFile(old_file).sheet_names
    new_sheets = pd.ExcelFile(new_file).sheet_names

    # اختيار الورقة
    col1, col2 = st.columns(2)
    with col1:
        old_sheet = st.selectbox("📄 اختر ورقة ERP", old_sheets, key="erp_sheet")
    with col2:
        new_sheet = st.selectbox("📄 اختر ورقة Cloud", new_sheets, key="cloud_sheet")

    # قراءة البيانات
    df_old = pd.read_excel(old_file, sheet_name=old_sheet)
    df_new = pd.read_excel(new_file, sheet_name=new_sheet)

    # تنظيف الأعمدة
    df_old.columns = df_old.columns.str.strip()
    df_new.columns = df_new.columns.str.strip()

    # محاولة التعرف على عمود الرقم الوظيفي
    id_column_old = [col for col in df_old.columns if "اسم" in col and "الموظف" in col]
    id_column_new = [col for col in df_new.columns if "اسم" in col and "الموظف" in col]

    if not id_column_old or not id_column_new:
        st.error("⚠️ لم يتم العثور على عمود 'اسم الموظف' في أحد الملفين.")
        st.write("أعمدة ERP:", df_old.columns.tolist())
        st.write("أعمدة Cloud:", df_new.columns.tolist())
    else:
        id_col_old = id_column_old[0]
        id_col_new = id_column_new[0]

        df_old = df_old.dropna(subset=[id_col_old])
        df_new = df_new.dropna(subset=[id_col_new])

        # استثناء الدوائر المحددة
        excluded_departments = ['HC.نادي عجمان للفروسية', 'PD.الشرطة المحلية لإمارة عجمان', 'RC.الديوان الأميري']
        if 'الدائرة' in df_old.columns:
            df_old = df_old[~df_old['الدائرة'].isin(excluded_departments)]
        if 'الدائرة' in df_new.columns:
            df_new = df_new[~df_new['الدائرة'].isin(excluded_departments)]

        # توحيد أسماء الأعمدة للرقم الوظيفي
        df_old = df_old.rename(columns={id_col_old: "EmployeeID"})
        df_new = df_new.rename(columns={id_col_new: "EmployeeID"})

        # دمج خارجي لاستخراج الموظفين غير المشتركين
        outer_merged = pd.merge(df_old, df_new, on="EmployeeID", how="outer", indicator=True)
        only_in_old = outer_merged[outer_merged["_merge"] == "left_only"]
        only_in_new = outer_merged[outer_merged["_merge"] == "right_only"]

        # دمج داخلي لاستخراج الفروقات
        merged = pd.merge(df_old, df_new, on="EmployeeID", how="inner", suffixes=('_old', '_new'))

        # استخراج الفروقات
        differences = []
        for _, row in merged.iterrows():
            emp_id = row["EmployeeID"]
            dept = row['الدائرة_old'] if 'الدائرة_old' in row else 'غير معروف'

            for col in df_old.columns:
                if col == "EmployeeID":
                    continue

                col_old = f"{col}_old"
                col_new = f"{col}_new"

                if col_old in merged.columns and col_new in merged.columns:
                    val_old = row[col_old]
                    val_new = row[col_new]

                    if pd.notna(val_old) and pd.notna(val_new) and val_old != val_new:
                        differences.append((emp_id, dept, col, val_old, val_new))

        # تبويبات
        tab1, tab2, tab3 = st.tabs(["📌 الموظفين فقط في ERP", "📌 الموظفين فقط في Cloud", "🔍 الفروقات بين الملفين"])

        with tab1:
            st.subheader("الموظفون الموجودون فقط في ملف النظام القديم (ERP)")
            if not only_in_old.empty:
                df_download1 = only_in_old.drop(columns=["_merge"]).reset_index(drop=True)
                st.dataframe(df_download1)

                buffer1 = BytesIO()
                df_download1.to_excel(buffer1, index=False)
                buffer1.seek(0)

                st.download_button(
                    label="⬇️ تحميل Excel",
                    data=buffer1,
                    file_name="الموظفين_فقط_في_ERP.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("لا يوجد موظفون حصريون في ERP.")

        with tab2:
            st.subheader("الموظفون الموجودون فقط في ملف النظام الجديد (Cloud)")
            if not only_in_new.empty:
                df_download2 = only_in_new.drop(columns=["_merge"]).reset_index(drop=True)
                st.dataframe(df_download2)

                buffer2 = BytesIO()
                df_download2.to_excel(buffer2, index=False)
                buffer2.seek(0)

                st.download_button(
                    label="⬇️ تحميل Excel",
                    data=buffer2,
                    file_name="الموظفين_فقط_في_Cloud.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("لا يوجد موظفون حصريون في Cloud.")

        with tab3:
            st.subheader("الفروقات بين بيانات النظامين")
            if differences:
                diff_df = pd.DataFrame(differences, columns=["الرقم الوظيفي", "الدائرة", "العمود", "القيمة القديمة", "القيمة الجديدة"])
                st.success(f"تم العثور على {len(diff_df)} فرق في البيانات.")

                changed_columns = diff_df['العمود'].unique().tolist()
                tabs = st.tabs(changed_columns)
                for i, col in enumerate(changed_columns):
                    with tabs[i]:
                        st.subheader(f"التغييرات في العمود: {col}")
                        st.dataframe(diff_df[diff_df['العمود'] == col].reset_index(drop=True))
            else:
                st.info("لا توجد اختلافات بين النظامين.")

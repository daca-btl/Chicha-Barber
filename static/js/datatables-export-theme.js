(function () {
  "use strict";

  if (typeof jQuery === "undefined" || !jQuery.fn.dataTable) {
    return;
  }

  var $ = jQuery;
  var dataTable = $.fn.dataTable;
  var brandName = "CHICHA BARBER STUDIO";
  
  var primaryColor = "000000";
  var darkColor = "111111";
  var lightColor = "FAFAFA";
  var borderColor = "E5E5E5";
  var excelPrimaryColor = "1F2933";
  var excelAccentColor = "D4AF37";
  var excelDarkColor = "263238";
  var excelStripeColor = "F7F4ED";

  function getReportTitle(table) {
    var $table = $(table.table().node());
    var $scope = $table.closest(".card");
    var heading = $scope
      .find(".card-header h1, .card-header h2, .card-header h3, .card-header h4, .card-header h5")
      .first()
      .text()
      .trim();

    if (!heading) {
      heading = $("main h1, main h2, main h3").first().text().trim();
    }

    return heading || "Reporte Administrativo";
  }

  function getExportDate() {
    return new Date().toLocaleString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  }

  function addXmlElement(xml, parent, name, attributes) {
    var element = xml.createElementNS(parent.namespaceURI, name);

    Object.keys(attributes || {}).forEach(function (key) {
      element.setAttribute(key, attributes[key]);
    });

    parent.appendChild(element);
    return element;
  }

  function addExcelStyle(xml, fonts, fills, cellFormats, fontOptions, fillColor, alignment) {
    var font = addXmlElement(xml, fonts, "font");
    addXmlElement(xml, font, "sz", { val: String(fontOptions.size || 10) });
    addXmlElement(xml, font, "name", { val: "Arial" });
    if (fontOptions.bold) {
      addXmlElement(xml, font, "b");
    }
    if (fontOptions.italic) {
      addXmlElement(xml, font, "i");
    }
    if (fontOptions.color) {
      addXmlElement(xml, font, "color", { rgb: fontOptions.color });
    }
    fonts.setAttribute("count", String(fonts.children.length));

    var fill = addXmlElement(xml, fills, "fill");
    var pattern = addXmlElement(xml, fill, "patternFill", { patternType: "solid" });
    addXmlElement(xml, pattern, "fgColor", { rgb: fillColor });
    addXmlElement(xml, pattern, "bgColor", { indexed: "64" });
    fills.setAttribute("count", String(fills.children.length));

    var format = addXmlElement(xml, cellFormats, "xf", {
      numFmtId: "0",
      fontId: String(fonts.children.length - 1),
      fillId: String(fills.children.length - 1),
      borderId: "1",
      applyFont: "1",
      applyFill: "1",
      applyBorder: "1"
    });

    if (alignment) {
      addXmlElement(xml, format, "alignment", alignment);
      format.setAttribute("applyAlignment", "1");
    }

    cellFormats.setAttribute("count", String(cellFormats.children.length));
    return cellFormats.children.length - 1;
  }

  function getCellText(cell) {
    var textNodes = cell.getElementsByTagName("t");
    var text = "";

    for (var index = 0; index < textNodes.length; index += 1) {
      text += textNodes[index].textContent;
    }

    return text.trim().toLowerCase();
  }

  function getExcelColumnName(columnIndex) {
    var columnName = "";
    var index = columnIndex + 1;

    while (index > 0) {
      var remainder = (index - 1) % 26;
      columnName = String.fromCharCode(65 + remainder) + columnName;
      index = Math.floor((index - 1) / 26);
    }

    return columnName;
  }

  function setRowStyle(row, style) {
    var cells = row.getElementsByTagName("c");
    for (var index = 0; index < cells.length; index += 1) {
      cells[index].setAttribute("s", String(style));
    }
  }

  function styleExcelExport(xlsx, config, table) {
    var sheet = xlsx.xl.worksheets["sheet1.xml"];
    var styles = xlsx.xl["styles.xml"];
    var fonts = styles.getElementsByTagName("fonts")[0];
    var fills = styles.getElementsByTagName("fills")[0];
    var cellFormats = styles.getElementsByTagName("cellXfs")[0];

    var titleStyle = addExcelStyle(
      styles,
      fonts,
      fills,
      cellFormats,
      { bold: true, color: "FF" + excelAccentColor, size: 16 },
      "FF" + excelPrimaryColor,
      { horizontal: "left", vertical: "center" }
    );
    var subtitleStyle = addExcelStyle(
      styles,
      fonts,
      fills,
      cellFormats,
      { color: "FF667085", size: 10 },
      "FFF3F4F6",
      { horizontal: "left", vertical: "center" }
    );
    var headerStyle = addExcelStyle(
      styles,
      fonts,
      fills,
      cellFormats,
      { bold: true, color: "FFFFFFFF" },
      "FF" + excelPrimaryColor,
      { horizontal: "center", vertical: "center", wrapText: "1" }
    );
    var stripeStyle = addExcelStyle(
      styles,
      fonts,
      fills,
      cellFormats,
      { color: "FF" + excelDarkColor },
      "FF" + excelStripeColor,
      { horizontal: "center", vertical: "center", wrapText: "1" }
    );
    var bodyStyle = addExcelStyle(
      styles,
      fonts,
      fills,
      cellFormats,
      { color: "FF" + excelDarkColor },
      "FFFFFFFF",
      { horizontal: "center", vertical: "center", wrapText: "1" }
    );

    var exportData = table.buttons.exportData(config.exportOptions || {});
    if (!exportData.header || !exportData.header.length) {
      return;
    }
    var expectedHeaders = exportData.header.map(function (header) {
      return String(header).replace(/<[^>]*>/g, "").trim().toLowerCase();
    });
    var rows = sheet.getElementsByTagName("row");
    var headerRow = null;
    var headerRowIndex = -1;

    for (var rowIndex = 0; rowIndex < rows.length; rowIndex += 1) {
      var cells = rows[rowIndex].getElementsByTagName("c");
      if (cells.length !== expectedHeaders.length) {
        continue;
      }

      var rowMatchesHeaders = true;
      for (var cellIndex = 0; cellIndex < cells.length; cellIndex += 1) {
        if (getCellText(cells[cellIndex]) !== expectedHeaders[cellIndex]) {
          rowMatchesHeaders = false;
          break;
        }
      }

      if (rowMatchesHeaders) {
        headerRow = rows[rowIndex];
        headerRowIndex = rowIndex;
        break;
      }
    }

    if (!headerRow) {
      return;
    }

    var rowNumber = parseInt(headerRow.getAttribute("r"), 10) || headerRowIndex + 1;
    headerRow.setAttribute("ht", "30");
    headerRow.setAttribute("customHeight", "1");
    setRowStyle(headerRow, headerStyle);

    var metadataRows = [];
    for (var metadataIndex = 0; metadataIndex < headerRowIndex; metadataIndex += 1) {
      if (rows[metadataIndex].getElementsByTagName("c").length) {
        metadataRows.push(rows[metadataIndex]);
      }
    }
    if (metadataRows.length) {
      metadataRows[0].setAttribute("ht", "32");
      metadataRows[0].setAttribute("customHeight", "1");
      setRowStyle(metadataRows[0], titleStyle);
    }
    if (metadataRows.length > 1) {
      metadataRows[1].setAttribute("ht", "22");
      metadataRows[1].setAttribute("customHeight", "1");
      setRowStyle(metadataRows[1], subtitleStyle);
    }

    for (var dataRowIndex = headerRowIndex + 1; dataRowIndex < rows.length; dataRowIndex += 1) {
      rows[dataRowIndex].setAttribute("ht", "22");
      rows[dataRowIndex].setAttribute("customHeight", "1");
      setRowStyle(
        rows[dataRowIndex],
        (dataRowIndex - headerRowIndex) % 2 === 1 ? stripeStyle : bodyStyle
      );
    }

    var worksheet = sheet.documentElement || sheet;
    var sheetData = sheet.getElementsByTagName("sheetData")[0];
    var cols = sheet.getElementsByTagName("cols")[0];
    if (!cols) {
      cols = worksheet.insertBefore(
        sheet.createElementNS(worksheet.namespaceURI, "cols"),
        sheetData
      );
    }

    var columnCount = expectedHeaders.length;
    for (var columnIndex = 0; columnIndex < columnCount; columnIndex += 1) {
      var maxLength = expectedHeaders[columnIndex].length;
      (exportData.body || []).forEach(function (row) {
        var value = row[columnIndex] == null ? "" : String(row[columnIndex]);
        value = value.replace(/<[^>]*>/g, "").trim();
        maxLength = Math.max(maxLength, value.length);
      });

      addXmlElement(sheet, cols, "col", {
        min: String(columnIndex + 1),
        max: String(columnIndex + 1),
        width: String(Math.min(40, Math.max(12, maxLength + 3))),
        customWidth: "1"
      });
    }

    var lastRow = rows[rows.length - 1].getAttribute("r") || String(rows.length);
    var filterRange = "A" + rowNumber + ":" + getExcelColumnName(columnCount - 1) + lastRow;
    var autoFilter = sheet.getElementsByTagName("autoFilter")[0];
    if (autoFilter) {
      autoFilter.setAttribute("ref", filterRange);
    } else {
      autoFilter = sheet.createElementNS(worksheet.namespaceURI, "autoFilter");
      autoFilter.setAttribute("ref", filterRange);
      worksheet.insertBefore(autoFilter, sheetData.nextSibling);
    }
  }

  // Estilo Personalizado para PDF
  function stylePdfExport(documentDefinition, config, table) {
    var reportTitle = getReportTitle(table);
    var columnCount = table.columns(config.exportOptions && config.exportOptions.columns).count();

    documentDefinition.pageSize = "A4";
    documentDefinition.pageOrientation = columnCount > 6 ? "landscape" : "portrait";
    documentDefinition.pageMargins = [36, 76, 36, 58];
    documentDefinition.defaultStyle = $.extend({}, documentDefinition.defaultStyle, {
      fontSize: 8.5,
      color: "#" + darkColor,
      alignment: "center" // Centrar contenido general
    });
    documentDefinition.styles = $.extend({}, documentDefinition.styles, {
      title: {
        fontSize: 16,
        bold: true,
        color: "#" + primaryColor,
        alignment: "center",
        margin: [0, 0, 0, 12]
      }
    });
    documentDefinition.info = $.extend({}, documentDefinition.info, {
      title: reportTitle,
      author: brandName,
      subject: "Reporte generado el " + getExportDate()
    });
    documentDefinition.header = function () {
      return {
        columns: [
          { text: brandName, bold: true, color: "#" + primaryColor, fontSize: 9, letterSpacing: 1 },
          { text: "REPORTE ADMINISTRATIVO", alignment: "right", color: "#666666", fontSize: 8, letterSpacing: 0.5 }
        ],
        margin: [36, 26, 36, 0]
      };
    };
    documentDefinition.footer = function (currentPage, pageCount) {
      return {
        columns: [
          { text: "Documento generado el " + getExportDate(), color: "#888888", fontSize: 8 },
          { text: currentPage + " / " + pageCount, alignment: "right", color: "#888888", fontSize: 8 }
        ],
        margin: [36, 0, 36, 22]
      };
    };

    documentDefinition.content.forEach(function (item) {
      if (!item.table) {
        return;
      }

      item.table.headerRows = 1;
      // Hacer que las columnas se distribuyan proporcionalmente para centrar la tabla en la página
      item.table.widths = Array(columnCount).fill("*");
      item.table.layout = {
        hLineColor: function () { return "#" + borderColor; },
        vLineColor: function () { return "#" + borderColor; },
        hLineWidth: function (lineIndex) { return lineIndex === 1 ? 1.5 : 0.5; },
        vLineWidth: function () { return 0.5; },
        paddingLeft: function () { return 6; },
        paddingRight: function () { return 6; },
        paddingTop: function () { return 7; },
        paddingBottom: function () { return 7; }
      };

      item.table.body.forEach(function (row, rowIndex) {
        row.forEach(function (cell, cellIndex) {
          var styledCell = typeof cell === "object" && cell !== null ? cell : { text: cell };

          if (rowIndex === 0) {
            styledCell.fillColor = "#" + primaryColor;
            styledCell.color = "#FFFFFF";
            styledCell.bold = true;
            styledCell.alignment = "center";
          } else {
            styledCell.color = "#" + darkColor;
            styledCell.alignment = "center"; // Centrado de datos en celdas
            if (rowIndex % 2 === 0) {
              styledCell.fillColor = "#" + lightColor;
            }
          }

          row[cellIndex] = styledCell;
        });
      });
    });
  }

  // Estilo Personalizado para Impresión (Print Window)
  function stylePrintExport(printWindow, config, table) {
    var document = printWindow.document;
    var reportTitle = getReportTitle(table);
    var style = document.createElement("style");
    
    style.textContent =
      "@page{size:A4;margin:18mm 14mm}" +
      "body{font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;color:#111;font-size:9.5pt;margin:0;padding:0}" +
      ".dt-report-brand{border-bottom:2px solid #000;margin-bottom:20px;padding:0 0 10px;display:flex;justify-content:space-between;align-items:center}" +
      ".dt-report-brand strong{color:#000;font-size:11pt;letter-spacing:2px;text-transform:uppercase}" +
      ".dt-report-brand span{color:#666;font-size:8pt;letter-spacing:1px;text-transform:uppercase}" +
      "h1{color:#000;font-size:18pt;font-weight:700;margin:16px 0 10px;text-align:center;text-transform:uppercase;letter-spacing:1px}" +
      "body>div{color:#555;font-size:8.5pt;margin:0 0 16px;text-align:center}" +
      "table{border-collapse:collapse!important;width:100%!important;margin:0 auto!important;font-size:9pt}" +
      "thead{display:table-header-group}" +
      "th{background:#000!important;color:#fff!important;text-align:center!important;padding:10px 8px!important;border:1px solid #000!important;text-transform:uppercase;font-size:8pt;letter-spacing:0.5px}" +
      "td{padding:9px 8px!important;border:1px solid #e5e5e5!important;text-align:center!important}" +
      "tbody tr:nth-child(even){background:#fafafa!important}" +
      "tr{page-break-inside:avoid}" +
      ".dt-report-footer{border-top:1px solid #e5e5e5;color:#888;font-size:8pt;margin-top:28px;padding-top:10px;text-align:center;letter-spacing:0.5px}" +
      "@media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}";

    document.head.appendChild(style);

    var brand = document.createElement("div");
    brand.className = "dt-report-brand";
    brand.innerHTML = "<strong>" + brandName + "</strong><span>Reporte Oficial</span>";
    document.body.insertBefore(brand, document.body.firstChild);

    var heading = document.body.querySelector("h1");
    if (heading) {
      heading.textContent = reportTitle;
    }

    var footer = document.createElement("div");
    footer.className = "dt-report-footer";
    footer.textContent = "Generado el " + getExportDate() + " · " + brandName;
    document.body.appendChild(footer);
  }

  if (
    dataTable.ext.buttons.excelHtml5 &&
    dataTable.ext.buttons.pdfHtml5 &&
    dataTable.ext.buttons.print
  ) {
    dataTable.ext.buttons.excelHtml5.customize = styleExcelExport;
    dataTable.ext.buttons.pdfHtml5.customize = stylePdfExport;
    dataTable.ext.buttons.print.customize = stylePrintExport;
  }

  $.extend(true, dataTable.defaults, {
    dom:
      '<"row d-flex justify-content-between align-items-center mb-3"<"col-sm-12 col-md-4"l><"col-sm-12 col-md-4 d-flex justify-content-center"B><"col-sm-12 col-md-4 d-flex justify-content-end"f>>' +
      '<"row"<"col-sm-12 d-flex justify-content-center"tr>>' +
      '<"row mt-3"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7 d-flex justify-content-end"p>>',
    buttons: [
      {
        extend: "excelHtml5",
        text: '<i class="bi bi-file-earmark-excel me-1"></i>Excel',
        className: "btn btn-sm btn-dark me-2 px-3 shadow-sm",
        title: function (config, table) { return getReportTitle(table); },
        filename: function (config, table) {
          return getReportTitle(table) + " - " + new Date().toLocaleDateString("es-ES").replace(/\//g, "-");
        },
        messageTop: function () { return "Exportado el " + getExportDate(); },
        exportOptions: { columns: ":not(:last-child)" }
      },
      {
        extend: "pdfHtml5",
        text: '<i class="bi bi-file-earmark-pdf me-1"></i>PDF',
        className: "btn btn-sm btn-dark me-2 px-3 shadow-sm",
        title: function (config, table) { return getReportTitle(table); },
        filename: function (config, table) {
          return getReportTitle(table) + " - " + new Date().toLocaleDateString("es-ES").replace(/\//g, "-");
        },
        messageTop: function () { return "Exportado el " + getExportDate(); },
        exportOptions: { columns: ":not(:last-child)" }
      },
      {
        extend: "print",
        text: '<i class="bi bi-printer me-1"></i>Imprimir',
        className: "btn btn-sm btn-outline-dark px-3 shadow-sm",
        title: function (config, table) { return getReportTitle(table); },
        messageTop: function () { return "Exportado el " + getExportDate(); },
        exportOptions: { columns: ":not(:last-child)" }
      }
    ]
  });
})();
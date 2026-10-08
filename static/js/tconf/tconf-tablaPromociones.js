$(document).ready(function() {
    var nombreTabla = "Listado de promociones";
    var fechaHoy = new Date()
        .toLocaleDateString("es-ES", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric"
        })
        .replace(/\//g, "-");
    var fechaConHora = new Date().toLocaleString("es-ES", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
    });

    $('#tablaPromociones').DataTable({
        "language": {
            "sProcessing": "Procesando...",
            "sLengthMenu": "Mostrar _MENU_ registros",
            "sZeroRecords": "No se encontraron resultados",
            "sEmptyTable": "Ningún dato disponible en esta tabla",
            "sInfo": "Mostrando registros del _START_ al _END_ de un total de _TOTAL_ registros",
            "sInfoEmpty": "Mostrando registros del 0 al 0 de un total de 0 registros",
            "sInfoFiltered": "(filtrado de un total de _MAX_ registros)",
            "sInfoPostFix": "",
            "sSearch": "Buscar:",
            "sUrl": "",
            "sInfoThousands": ",",
            "sLoadingRecords": "Cargando...",
            "oPaginate": {
                "sFirst": "Primero",
                "sLast": "Último",
                "sNext": "Siguiente",
                "sPrevious": "Anterior"
            },
            "oAria": {
                "sSortAscending": ": Activar para ordenar la columna de manera ascendente",
                "sSortDescending": ": Activar para ordenar la columna de manera descendente"
            }
        },
        "paging": true,
        "lengthChange": true,
        "searching": true,
        "ordering": true,
        "info": true,
        "autoWidth": false,
        "responsive": true,
        "pageLength": 10,
        "lengthMenu": [[5, 10, 25, 50, -1], [5, 10, 25, 50, "Todos"]],
        "dom": '<"row d-flex justify-content-between align-items-center mb-3"<"col-sm-12 col-md-4"l><"col-sm-12 col-md-4 d-flex justify-content-center"B><"col-sm-12 col-md-4 d-flex justify-content-end"f>>' +
            '<"row"<"col-sm-12"tr>>' +
            '<"row mt-3"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7 d-flex justify-content-end"p>>',
        "buttons": [
            {
                "extend": "excelHtml5",
                "text": '<i class="bi bi-file-earmark-excel"></i> Excel',
                "className": "btn btn-sm dt-btn-excel me-2",
                "filename": nombreTabla + " - " + fechaHoy,
                "title": nombreTabla,
                "messageTop": "Exportado el: " + fechaConHora,
                "exportOptions": { "columns": ":not(:last-child)" }
            },
            {
                "extend": "pdfHtml5",
                "text": '<i class="bi bi-file-earmark-pdf"></i> PDF',
                "className": "btn btn-sm dt-btn-pdf me-2",
                "filename": nombreTabla + " - " + fechaHoy,
                "title": nombreTabla,
                "messageTop": "Exportado el: " + fechaConHora,
                "exportOptions": { "columns": ":not(:last-child)" }
            },
            {
                "extend": "print",
                "text": '<i class="bi bi-printer"></i> Imprimir',
                "className": "btn btn-sm dt-btn-print",
                "title": nombreTabla,
                "messageTop": "Exportado el: " + fechaConHora,
                "exportOptions": { "columns": ":not(:last-child)" }
            }
        ],
        "columnDefs": [
            { "orderable": false, "targets": [0, 3] }, // Deshabilita la ordenación en las columnas de Imagen y Acciones
            { "searchable": false, "targets": [0, 3] } // Deshabilita la búsqueda en las columnas de Imagen y Acciones
        ]
    });
});
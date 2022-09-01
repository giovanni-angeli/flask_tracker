var tasksMilestones = []
var tasksList = null
var projectList = null
var currentTaskList = []
var milestoneFilter = null
var projectFilter = null

function formatAsPercent(num) {
  percentageNum = Intl.NumberFormat('default', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);

  if (percentageNum == 'NaN%') percentageNum = '0%'

  return percentageNum
}

let setup_global_vars = function() {
  if (tasksList == null || projectList == null) return;

  console.log(tasksList)
  console.log(projectList)

}

function init_html(){

  console.debug('fetch /api/v1/task')
  fetch('/api/v1/task')
    .then((response) => response.json())
    .then((data) => {
      tasksList = data.results
      setup_global_vars()
    }).catch(err => console.error(err));

  console.debug('fetch /api/v1/task')
  fetch('/api/v1/project')
    .then((response) => response.json())
    .then((data) => {
      projectList = data.results
      setup_global_vars()
    }).catch(err => console.error(err));

  console.log('end of init_html() ')

  // inserire un loading spinner?

}

function showTasksByStatus(){

  if (tasksList == null) return;

  // clear all select2 selections
  $('.js-example-placeholder-multiple').val(null).trigger('change');

  tasksByStatus(tasksList)
}

function tasksByStatus(taskList, resetFilters=true){

  if (taskList == null) return;

  $("#table-status-tasks tbody tr").remove()
  $("#filters").show()
  // $("filters").attr("display","inline-block");

  var total_tasks = taskList.length
  var new_tasks = 0
  var open_tasks = 0
  var in_progress_tasks = 0
  var suspended_tasks = 0
  var test_tasks = 0
  var closed_tasks = 0
  var invalid_tasks = 0
  var task_milestones = []

  for (task of taskList) {
    switch (task.status){
      case "new":
        new_tasks++
        break
      case "open":
        open_tasks++
        break
      case "in_progress":
        in_progress_tasks++
        break
      case "suspended":
        suspended_tasks++
        break
      case "test":
        test_tasks++
        break
      case "closed":
        closed_tasks++
        break
      case "invalid":
        invalid_tasks++
        break
      default:
        console.log(`Sorry, we are out of ${task.status}.`);
    }
    if (task.milestone !== undefined && !task_milestones.includes(task.milestone)) { 
      task_milestones.push(task.milestone)
    }
  }

  var task_numbers = [total_tasks, new_tasks, open_tasks, in_progress_tasks, suspended_tasks,
                      test_tasks, closed_tasks, invalid_tasks]
  const task_col = ['Total Tasks', 'New Tasks', 'Open Tasks', 'In progess Tasks', 'Suspended Tasks',
                    'Test Tasks', 'Closed Tasks', 'Invalid Tasks']
  for (const [i, elm] of task_col.entries()) {
    var table = $('#table-status-tasks')
    var tr = $('<tr>')
    var percentage = formatAsPercent(task_numbers[i]/total_tasks)
    tr.append('<td class="table-status-tasks-td">' + elm + '</td>')
    tr.append('<td class="table-status-tasks-td">' + task_numbers[i] + ' / ' + total_tasks + '</td>')
    tr.append('<td class="table-status-tasks-td">' + percentage + '</td>')
    table.find('tbody').append(tr)
  }

  var labels = task_col.slice(1)
  var data = task_numbers.slice(1)
  var colors = [
    '#26D7AE',  // new
    '#52D726',  // open
    '#FFEC00',  // in progress
    '#FF7300',  // suspended
    '#C758D0',  // test
    '#007ED6',  // closed
    '#FF0000',  // invalid
  ]
  drawPieChart(labels, data, colors)


  if (task_milestones && projectList) {
    if ( resetFilters ) populateStatusFilters(task_milestones, projectList)
  }

}

function populateStatusFilters(milestones, projects){
  var sortedUniqueMilestones = [...new Set(milestones)]
  var sortedUniqueProjects = [...new Set(projects)]
  $('#filter-by-milestone').empty()
  $('#filter-by-project').empty()

  for (milestone of sortedUniqueMilestones){
    $('#filter-by-milestone').append($('<option>', {
        value: milestone,
        text: milestone
    }));
  }

  for (project of sortedUniqueProjects){
    $('#filter-by-project').append($('<option>', {
        value: project.id,
        text: project.name
    }));
  }

}

function drawPieChart(labels, data, colors){
  var config = {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        label: 'Pie Chart',
        data: data,
        backgroundColor: colors,
        hoverOffset: 4
      }]
    },
    options: {
      responsive: true
    }
  };
  var ctx = document.getElementById("chart-area").getContext("2d");
  if (window.statusPie){ window.statusPie.destroy() }
  window.statusPie = new Chart(ctx, config);
}

function applyFilter(){

  console.log('milestoneFilter: ',milestoneFilter)
  console.log('projectFilter: ',projectFilter)

  const modelList = tasksList.slice()
  const filter = {
    milestone: milestoneFilter,
    project_id: projectFilter
  }
  console.log(filter)

  var filteredModelList = tasksList.filter(item => {
    for (let key in filter) {
      if (filter[key] === undefined ){
        continue
      }
      if (item[key] === undefined || item[key] != filter[key])
        return false;
    }
    return true;
  })
  console.log(filteredModelList)
  tasksByStatus(filteredModelList, false)
}

function resetFilter(){
  showTasksByStatus()
}

// TODO: check for this func
function filterTasks(term){
  if (tasksList == null) return;

  var filteredTaskList = []
  console.log('term : ', term)

  if (term){
    console.debug('filtering tasksList')
    for ( task of tasksList ) {
      if ( task.milestone !== undefined ) {
        if( task.milestone == term ){
          filteredTaskList.push(task);
        }
      }
    }
  } else { filteredTaskList = tasksList.slice()}

  console.debug(filteredTaskList)
  tasksByStatus(filteredTaskList)
}

$(document).ready(function () {
  //change selectboxes to selectize mode to be searchable
  $("#filter-by-milestone").select2({
    width: 'resolve', // need to override the changed default
    maximumSelectionLength: 1,
    allowClear: false
  })

  $("#filter-by-project").select2({
    width: 'resolve', // need to override the changed default
    maximumSelectionLength: 1,
    allowClear: false
  })

  $("#filter-by-milestone").on('change', function() {
    var current_val = $(this).val()[0]
    console.debug(current_val)
    milestoneFilter = current_val 
  });

  $("#filter-by-project").on('change', function() {
    var current_val = $(this).val()[0]
    console.debug(current_val)
    projectFilter = current_val
  });

});

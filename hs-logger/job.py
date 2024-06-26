from logger import Logger
import wx
import time
import numpy as np
import os
# from apscheduler.schedulers.background import BackgroundScheduler


class Job(object):
    def __init__(self, spec, inst_drivers, frame):
        self.inst_drivers = inst_drivers
        self.spec = spec
        frame_log = Text_Log(frame.job_disp_log)
        self.logger = Logger(self, inst_drivers, frame_log)
        self.frame = frame
        self.frame.SetTitle(f"{spec.get('job_name', '')}")  # Was u""
        self.graphs = []
        self.frame.add_table(4, len(spec.get("logged_operations", {}))+len(spec.get("references", {}))-1)
        self.auto_profile = AutoProfile(self)
        self.frame.add_profile_table(self.auto_profile)
        self.n = 0
        self.pauseStart = time.time() / 60

        # self.sched = BackgroundScheduler()
        # self.sched.add_job(func=self.update_graphs, trigger='interval', seconds=5)
        # self.sched.add_job(func=self.update_table, trigger='interval', seconds=5)
        # self.sched.add_job(func=self.update_autoprofile, trigger='interval', seconds=5)
        # self.sched.start()

    def update_cycle(self):
        self.update_table()
        self.update_graphs()
        self.update_autoprofile()

    def load_profile(self):
        pass

    def auto_profile_actions(self, actions):
        self.frame.reading_text.SetLabel("Writing:")  # Was u""
        for inst_op, val in actions:
            # inst_op = inst_op.split(".")
            self.frame.current_reading.SetLabel(f"{inst_op} = {val}")  # Was u""
            if inst_op != "":
                i_id, op_id = inst_op.split(".")
                op_check = self.logger.instruments.get(i_id).spec.get("operations", {}).get(op_id, {}).get("check_set", "")
                inst_driver = self.inst_drivers.get(i_id)
                try:
                    if op_check == "":
                        inst_driver.write_instrument(op_id, [val])
                    else:
                        curset = self.auto_profile.check_instrument(i_id, op_check)
                        i = 0
                        while float(curset) != float(val) and i < 5:
                            i = i + 1
                            print(f"Write attempt {i}")
                            inst_driver.write_instrument(op_id, [val])
                            curset = self.auto_profile.check_instrument(i_id, op_check)
                            print(f"{float(val)} = {float(curset)}?")
                except:
                    print("auto profile action error")
        self.frame.reading_text.SetLabel("Waiting...")  # Was u""
        self.frame.current_reading.SetLabel("")  # Was u""

    def update_autoprofile(self):
        self.auto_profile.update()

    def new_autoprofile_col(self):
        name, inst_ops = self.frame.get_autoprofile_new_action_dlg()
        if name != "cancelled":
            self.auto_profile.new_set_op(name, inst_ops)

    def next_point(self):
        self.auto_profile.next_point()

    def save_points(self):
        self.auto_profile.save_points()

    def new_point(self):
        self.auto_profile.new_point()

    def reset(self):
        pass

    def new_run(self):
        pass

    def next_n(self, n):
        pass

    def last_n(self, n):
        pass

    def assured_soak(self):
        pass

    def pause(self):
        self.logger.pause()
        self.pauseStart = time.time() / 60

    def resume(self):
        self.logger.delay = self.logger.delay + (time.time() / 60) - self.pauseStart
        self.logger.resume()

    def start(self):
        self.logger.start()
        self.auto_profile.point_start_time = time.time() / 60
        self.auto_profile.move_to_point(self.auto_profile.current_point)

    def stop(self):
        self.logger.stop()
        self.frame.Destroy()
        # self.sched.shutdown()

    def add_graph(self, plt):  # Adds the graph to the list of graphs
        graph_names = []
        for i in range(len(self.graphs)):
            graph_names.append(self.graphs[i][0][1])
        axis_choices = self.logger.opref.copy()
        name, x, y = self.frame.get_add_graph_dialog(axis_choices)
        while graph_names.count(name) > 0:
            name = name + "\'"
        if name == "cancelled":
            return "cancelled"
        else:  # Procedure wasn't cancelled
            self.graphs.append([(plt, name), (x, y)])
            self.update_graphs()
            return name

    def append_graph(self, plt):  # Adds a new line to the selected graph
        graph_choices = []
        for i in range(len(self.graphs)):
            graph_choices.append(self.graphs[i][0][1])
        axis_choices = self.logger.opref.copy()
        index, y = self.frame.get_append_graph_dialog(graph_choices, axis_choices)
        axis_check = []
        for i in range(len(self.graphs[index]) - 1):
            axis_check.append(self.graphs[index][i + 1][1])
        if index != -1:  # Procedure wasn't cancelled
            if axis_check.count(y) == 0:
                x = self.graphs[index][1][0]
                self.graphs[index].append((x, y))
                self.update_graphs()
            else:
                print(f"{y} already in {self.graphs[index][0][1]}.")

    def detract_graph(self, plt):  # Removes a line from the selected graph
        graph_choices = []
        for i in range(len(self.graphs)):
            graph_choices.append(self.graphs[i][0][1])
        graph_index = self.frame.get_detract_graph_graph_dialog(graph_choices)
        if graph_index > -1:  # Procedure wasn't cancelled
            axis_choices = []
            for i in range(len(self.graphs[graph_index])-1):
                axis_choices.append(self.graphs[graph_index][i+1][1])
            if len(axis_choices) > 1:
                axis_index = self.frame.get_detract_graph_axis_dialog(axis_choices)
                if axis_index > -1:  # Procedure wasn't cancelled
                    self.graphs[graph_index].pop(axis_index+1)
                    self.update_graphs()
            else:
                print("Can't detract last line.")

    def remove_graph(self, plt):  # Removes the selected graph
        graph_choices = []
        for i in range(len(self.graphs)):
            graph_choices.append(self.graphs[i][0][1])
        index = self.frame.get_remove_graph_dialog(graph_choices)
        if index > -1:  # Procedure wasn't cancelled
            self.graphs.pop(index)
        return index + 3

    def update_graphs(self):  # Updates the data depicted in the graphs
        for g in self.graphs:  # g in form of [[graph object, name], [x1, y1], [x2, y2], etc...]
            leg = []
            plt = g[0][0].figure.gca()
            plt.clear()
            for i in range(len(g)):
                if i != 0:
                    x = g[i][0]
                    y = g[i][1]
                    inst_x, op = x.split('.')
                    if inst_x == "reference":
                        x_val = [d.get(x) for d in self.logger.storeref]
                    else:
                        x_val = [d[1].get(x) for d in self.logger.store]
                    inst_y, op = y.split('.')
                    if inst_y == "reference":
                        y_val = [d.get(y) for d in self.logger.storeref]
                        y_name = op
                    else:
                        y_val = [d[1].get(y) for d in self.logger.store]
                        if inst_y != "time":
                            try:
                                y_name = self.logger.job_spec["details"][inst_y][op]
                            except KeyError:
                                y_name = self.logger.instruments.get(inst_y).spec["operations"][op]["name"]
                        else:
                            y_name = op
                    leg.append(y_name)
                    plt.plot(x_val, y_val, ".-")
            plt.legend(leg)
            g[0][0].canvas.draw()

    def generate_graph(self, graph):
        self.graphs.append(graph)
        self.update_graphs()

    def update_table(self):
        self.frame.update_table(0)


class AutoProfile(object):
    def __init__(self, job):
        self.job = job
        self.profile_header = ["Points", "Soak", "Assured"]
        self.points = 1
        self.points_list = [1]
        self.soak = [50]
        self.assured = [0]
        self.operations = {}  # format "Name":(inst_op,[points])
        self.title = ""  # The first line of the autoprofile is the name of the file.
        self.h_name = []  # The second line of the autoprofile contains the names.
        self.h_set = []  # The third line of the autoprofile contains the commands to set the setpoints.
        # self.h_check = []
        # self.h_actual = []
        self.stdev_list = []  # This list contains the data required for the assured switch.
        self.current_stdev = ""  # This defines what the standard deviation is of.
        self.a_dif = 0.1  # This is the difference between the actual and measured values that assured allows.
        self.a_std = 0.1  # This is the standard deviation of measured values that assured allows.

        self.current_point = 0
        self.point_start_time = time.time() / 60
        self.transtime = ""  # Was u""

    def reset(self):
        self.profile_header = ["Points", "Soak", "Assured"]
        self.points = 1
        self.points_list = [1]
        self.soak = [1]
        self.assured = [0]
        self.operations = {}
        self.job.frame.job_book.SetPageText(2, "Profile")
        self.grid_refresh()

    def load_file(self, direc, fn):
        grid = self.job.frame.grid_auto_profile
        rows1 = len(self.profile_header)
        cols1 = self.points
        try:
            with open(os.path.join(direc, fn), 'r') as file:
                titles = file.readline().strip().split(',')
                self.title = titles[0]
                while self.title[0] != 'a':  # Remove "ï»¿" from first item
                    self.title = self.title[1:]
                self.job.frame.job_book.SetPageText(2, self.title)
                self.h_name = file.readline().strip().split(',')
                self.profile_header = self.h_name.copy()
                self.h_set = file.readline().strip().split(',')
                # self.h_check = file.readline().strip().split(',')
                # self.h_actual = file.readline().strip().split(',')
                d1 = {}
                for name, inst_op in zip(self.h_name, self.h_set):
                    d1[name] = (inst_op, [])
                for line in file:
                    line = line.strip().split(',')
                    for i in range(len(self.h_name)):
                        name = self.h_name[i]
                        d1[name][1].append(line[i])
                # Extra bit to remove the mandatory fields from the operations list
                # Reset the lists
                self.points_list = []
                self.soak = []
                self.assured = []
                # Fill the lists again
                for i in range(len(d1[self.h_name[0]][1])):
                    self.points_list.append(d1["Points"][1][i])
                    self.soak.append(d1["Soak"][1][i])
                    self.assured.append(d1["Assured"][1][i])
                # Remove the data from d1
                d1.pop("Points")
                d1.pop("Soak")
                d1.pop("Assured")
                # Back to normal code
                self.points = len(d1[self.h_name[3]][1])
                self.operations = d1

        except ValueError as e:
            print(e)
            print('not a valid autoprofile')
        except OSError as e:
            print(e)
            print('not a valid autoprofile')

        # bSizer = self.job.frame.bSizer181
        # self.job.frame.grid_auto_profile.Destroy()
        # bSizer.Remove(0)
        # grid = wx.grid.Grid(self.job.frame.auto_profile, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        # self.job.frame.grid_auto_profile = grid
        # bSizer.Prepend(grid, 1, wx.ALL | wx.EXPAND, 5)
        # self.job.frame.auto_profile.Layout()
        # self.job.frame.add_profile_table(self)
        self.move_to_point(self.current_point)

    def new_set_op(self, name, inst_ops, default=0):
        points = [0 for _ in range(self.points)]
        self.operations[name] = (inst_ops, points)
        self.h_name.append(name)
        self.profile_header = self.h_name.copy()
        self.h_set.append(inst_ops)
        grid = self.job.frame.grid_auto_profile
        # msg = wx.grid.GridTableMessage(grid.table,
        #                                wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED, 1)
        # grid.ProcessTableMessage(msg)
        self.grid_refresh()

    def new_point(self):
        self.points += 1
        self.points_list.append(self.points)
        self.soak.append(self.soak[-1])
        self.assured.append(self.assured[-1])
        op2 = {}
        for name, op_pts in self.operations.items():
            op = op_pts[0]
            pts = op_pts[1]
            pts.append(pts[-1])
            op2[name] = (op, pts)
        self.operations = op2
        # grid = self.job.frame.grid_auto_profile
        # msg = wx.grid.GridTableMessage(grid.table,
        #                                wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, 1)
        # grid.ProcessTableMessage(msg)
        self.grid_refresh()

    def set_value(self, name, point, value):  # to check for out of range and name not found
        if name == "Soak":
            self.soak[point] = value
        elif name == "Assured":
            self.assured[point] = value
        elif name == "Points":
            self.points_list[point] = value
        else:
            op_pts = self.operations.get(name)  # check
            op_pts[1][point] = value

    def get_value(self, name, point):  # to check for out of range and name not found
        if name == "Soak":
            value = self.soak[point]
        elif name == "Assured":
            value = self.assured[point]
        elif name == "Points":
            value = self.points_list[point]
        else:
            op_pts = self.operations.get(name)  # check
            value = op_pts[1][point]
        return value

    def get_header(self):
        return self.profile_header

    def get_current_point(self):
        return self.current_point

    def next_point(self):
        self.job.logger.point_to_file()
        if self.points == self.current_point+1:
            self.move_to_point(0)
        else:
            self.move_to_point(self.current_point+1)

    def save_points(self):
        self.job.logger.point_to_file()

    def move_to_point(self, point):
        self.current_point = point
        self.grid_refresh()
        self.point_start_time = time.time() / 60
        actions = []
        if not self.job.logger.paused:
            for inst_op, vals in self.operations.values():
                if vals[point] != "":  # "" will not change the set point
                    actions.append((inst_op, vals[point]))
        self.job.auto_profile_actions(actions)


    def update(self):
        t1 = self.point_start_time + float(self.soak[self.current_point])  # - self.job.logger.delay  # if paused
        index = 2 + int(self.assured[self.current_point])
        timeleft = (t1 - (time.time()/60))
        if index < 3:
            if timeleft < 0:
                self.transtime = "Now"  # Was u""
                self.next_point()
            else:
                timeleft = round(timeleft, 1)
                self.transtime = f"{timeleft}"  # Was u""
        else:
            inst, ops = self.h_set[index].split('.')
            opc = self.job.logger.instruments.get(inst).spec.get("operations", {}).get(ops, {}).get("check_set", "")
            opa = self.job.logger.instruments.get(inst).spec.get("operations", {}).get(ops, {}).get("check_actual", "")
            # inst, opc = self.h_check[index].split('.')
            # inst, opa = self.h_actual[index].split('.')
            if opc == "" or opa == "":
                if timeleft < 0:
                    self.transtime = "Now"  # Was u""
                    self.next_point()
                else:
                    timeleft = round(timeleft, 1)
                    self.transtime = f"{timeleft}"  # Was u""
            else:
                value1 = self.check_instrument(inst, opc)
                value2 = self.check_instrument(inst, opa)
                if opa == self.current_stdev:
                    self.stdev_list.append(value2)  # If this is the same operation as last time, append the data.
                else:
                    self.current_stdev = opa[index]  # Otherwise, start a new array for the new operation.
                    self.stdev_list = []
                    self.stdev_list.append(value2)

                # if timeleft < 0:  # Modify this order so that time is after checks, for constant delay after settling.
                #     dif = value2 - value1
                #     std = self.stdev()
                #     if abs(dif) < self.a_dif:
                #         if std < self.a_std:
                #             self.transtime = "Now"  # Was u""
                #             self.next_point()
                #         else:
                #             self.transtime = f"Waiting till stdev ({std}) is less than {self.a_std}."  # Was u""
                #     else:
                #         self.transtime = f"Waiting till ({dif}) is less than {self.a_dif}."  # Was u""
                # else:
                #     self.transtime = f"{timeleft}"  # Was u""

                dif = value2 - value1
                if abs(dif) < self.a_dif:  # Check if the value is relatively accurate
                    std = self.stdev()
                    if std < self.a_std:  # Check if the value is relatively precise
                        if timeleft < 0:  # Check if the value has been accurate and precise for long enough
                            self.transtime = "Now"  # Was u""
                            self.next_point()
                        else:
                            self.transtime = f"{timeleft}"  # Was u""
                    else:
                        self.point_start_time = time.time() / 60
                        self.transtime = f"Waiting till stdev ({std}) is less than {self.a_std}."  # Was u""
                else:
                    self.point_start_time = time.time() / 60
                    self.transtime = f"Waiting till ({dif}) is less than {self.a_dif}."  # Was u""


    def check_instrument(self, inst_id, operation_id):
        inst = self.job.logger.instruments.get(inst_id)
        result = inst.read_instrument(operation_id)
        return result[1]

    def stdev(self):
        if self.job.logger.window < len(self.stdev_list):
            std = np.std(self.stdev_list[-self.job.logger.window:])
        else:
            std = np.std(self.stdev_list)
        return std

    def highlight_row(self):
        grid = self.job.frame.grid_auto_profile
        for col in range(len(self.profile_header)):
            for row in range(self.points):
                grid.SetCellBackgroundColour(row, col, wx.Colour(255, 255, 255))
        for col in range(len(self.profile_header)):
            grid.SetCellBackgroundColour(self.current_point, col, wx.Colour(230, 235, 245))

    def grid_refresh(self):
        self.highlight_row()
        grid = self.job.frame.grid_auto_profile
        # Fix the number of rows and columns
        # currows = grid.GetNumberRows()
        # desrows = self.points
        # print(currows, desrows)
        # if currows < desrows:
        #     grid.AppendRows(desrows - currows)
        # elif currows > desrows:
        #     grid.DeleteRows(desrows - 1, currows - desrows)
        # curcols = grid.GetNumberCols()
        # descols = len(self.get_header())
        # print(curcols, descols)
        # if curcols < descols:
        #     grid.AppendCols(descols - curcols)
        # elif curcols > descols:
        #     grid.DeleteCols(descols - 1, curcols - descols)
        # Refresh the table
        grid.AutoSizeRows()
        # grid.AutoSizeColumns() TODO
        grid.ForceRefresh()


class Text_Log(object):
    def __init__(self, textctrl):
        self.out = textctrl

    def write(self, text):
        text = str(text)+'\n'
        self.out.WriteText(text)

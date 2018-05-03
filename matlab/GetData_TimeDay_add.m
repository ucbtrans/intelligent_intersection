function [EventsDayMag, EventsDayRadars,EventsDayRadars2, PhasesDay, BoundariesPhases, BoundariesRadar, BoundariesMag,filen] = GetData_TimeDay_add(Date, Time, scope, IDsRadar, IDsMag, Merged)
    
    s = datestr(Date,'yyyy-mmdd');
%     if Merged
%         load(['G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\PedData\detEvents\Mag_PST_Merged_' s '.mat']);
%         EventsDayMag = EventsDayMagMerged;
%     else
%         load(['G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\PedData\detEvents\Mag_PST_' s '.mat']);
%     end
%     load(['G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\PedData\detEvents\Mag_PST_' s '.mat']);
%     filen=['G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\PedData\ped\Radar_PST_' s '_label.mat'];
%     disp(filen);
%     load(filen);
%     load(['G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\PedData\ped\Radar_PST_' s '.mat']);
%     load(['G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\PedData\SP\Phase_PST_' s '.mat']);
%     
    load(['Mag_PST_' s '.mat']);
    filen=['Radar_PST_' s '_label.mat'];
    disp(filen);
    load(filen);
    load(['Radar_PST_' s '.mat']);
    load(['Phase_PST_' s '.mat']);

    
    TimeLeft = Time - scope/2;
    TimeRight = Time + scope/2;
    
    BoundariesRadar = zeros(length(IDsRadar),4);
    BoundariesMag = ones(length(IDsMag),2);
    BoundariesPhases = zeros(16,2);
    
    % radars
    for id = IDsRadar
        index = find(strcmp(id, [EventsDayRadars.id]));
%         disp(size(TimeLeft));
%         disp(size(EventsDayRadars(index).TimeDetect));
%         disp(id);
        index
        j = find(EventsDayRadars(index).TimeDetect>TimeLeft, 1);
        
        if ~isempty(j) 
            if (j>1) && (EventsDayRadars(index).TimeUndetect(j-1) > TimeLeft)
                BoundariesRadar(index,1) = j-1;
            else
                BoundariesRadar(index,1) = j;
            end
        end
        
        j = find(EventsDayRadars(index).TimeUndetect < TimeRight,1,'last');
        if ~isempty(j) 
            if (j<length(EventsDayRadars(index).TimeDetect)) && (EventsDayRadars(index).TimeDetect(j+1) < TimeRight)
                BoundariesRadar(index,2) = j+1;
            else
                BoundariesRadar(index,2) = j;
            end
        end
    
%         id
%         index
        j = find((EventsDayRadars(index).TimeDetect <= Time) .* (EventsDayRadars(index).TimeUndetect >= Time));
        BoundariesRadar(index,3) = ~isempty(j);
        if ~isempty(j)
            BoundariesRadar(index,4)=j;
        end
            
    end
    
    
    % Mag Sensors
    for id = IDsMag
        index = find(strcmp(id, [EventsDayMag.id]));
        if ~isempty(index)
            j = find(EventsDayMag(index).TimeDetect > TimeLeft,1);

            if ~isempty(j)
                if (j>1) && (EventsDayMag(index).TimeUndetect(j-1) > TimeLeft)
                    BoundariesMag(index,1) = j-1;
                else
                    BoundariesMag(index,1) = j;
                end
            else
                BoundariesMag(index,1) = length(EventsDayMag(index).TimeDetect);
            end

            j = find(EventsDayMag(index).TimeUndetect < TimeRight,1,'last');
            if ~isempty(j)
                if (j < length(EventsDayMag(index).TimeDetect)) && (EventsDayMag(index).TimeDetect(j+1) < TimeRight)
                    BoundariesMag(index,2) = j+1;
                else
                    BoundariesMag(index,2) = j;
                end
            end
        end
    end
    
    
    
    % traffic lights phases
    for id = [1,2,4,5,6,8,13,14,15,16]
        j = find(PhasesDay(id).TimeDetect > TimeLeft,1);
        if ~isempty(j)
            if (j>1) && (PhasesDay(id).TimeUndetect(j-1) > TimeLeft)
                BoundariesPhases(id,1) = j-1;
            else
                BoundariesPhases(id,1) = j;
            end
        else
            BoundariesPhases(id,1) = length(PhasesDay(id).TimeDetect);
        end
        
        j = find(PhasesDay(id).TimeUndetect < TimeRight,1, 'last');
        if ~isempty(j)
            if (j < length(PhasesDay(id).TimeDetect) && (PhasesDay(id).TimeDetect(j+1) < TimeRight))
                BoundariesPhases(id,2) = j+1;
            else
                BoundariesPhases(id,2) = j;
            end
        end
    end
    
end